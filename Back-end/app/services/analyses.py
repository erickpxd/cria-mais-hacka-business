"""Conferência automática de uma versão da arte.

Verificações (regras + OCR, sem IA generativa):
  1. preço da arte x preço do briefing
  2. ortografia dos textos da arte (LanguageTool local)
  3. margem: texto muito perto da borda (geometria)
Tudo vira "achados" que a PESSOA decide aceitar ou rejeitar. Nada é aplicado sozinho.
"""
import asyncio
import difflib
import logging
import re

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import Achado, Analise, Arte, Projeto, VersaoArte
from app.services import armazenamento, ocr, ortografia
from app.services.briefing import RE_PRECO, formatar_preco
from app.services.erros import ErroNegocio

log = logging.getLogger(__name__)


def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower()).strip()


def _regiao(l: ocr.LinhaTexto, W: int, H: int) -> dict:
    return {"x": l.x, "y": l.y, "w": l.w, "h": l.h,
            "nx": l.x / W, "ny": l.y / H, "nw": l.w / W, "nh": l.h / H,
            "largura_imagem": W, "altura_imagem": H}


def _palavras_ignoradas(projeto: Projeto) -> set[str]:
    base = " ".join(filter(None, [projeto.nome, projeto.produto, projeto.informacoes_obrigatorias,
                                  projeto.orientacoes, " ".join(settings.ortografia_ignorar)]))
    return {w for w in re.findall(r"\w+", base.lower()) if len(w) >= 3}


def _pagina_ref(projeto: Projeto, chave: str) -> str | None:
    campo = (projeto.briefing_campos or {}).get(chave) or {}
    if campo.get("pagina"):
        return f"briefing, página {campo['pagina']}"
    return "briefing" if projeto.briefing_arquivo else None


async def analisar_versao(db: Session, versao: VersaoArte, projeto: Projeto) -> Analise:
    if versao.analise:  # reanálise: descarta a anterior
        db.delete(versao.analise)
        db.flush()

    img = cv2.imdecode(np.frombuffer(armazenamento.ler(versao.arquivo), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ErroNegocio(400, "Não foi possível abrir a imagem da arte.")
    H, W = img.shape[:2]

    motor = ocr.obter_motor()
    todas = await asyncio.to_thread(motor.ler, img)
    linhas = [l for l in todas if l.texto.strip() and l.confianca >= settings.ocr_confianca_min]

    achados: list[dict] = []
    aplicadas: list[str] = []
    notas: list[str] = []

    # ---------- 1) PREÇO ----------
    if projeto.preco_centavos is None:
        notas.append("Preço: não informado no briefing, não foi possível confirmar.")
    else:
        encontrados = []  # (linha, texto_do_preco, centavos)
        for l in linhas:
            for m in RE_PRECO.finditer(l.texto):
                encontrados.append((l, m.group(0), int(m.group(1).replace(".", "")) * 100 + int(m.group(2))))
        if not encontrados:
            notas.append("Preço: nenhum preço foi encontrado na arte.")
        else:
            aplicadas.append("preco")
            if projeto.preco_centavos not in {c for _, _, c in encontrados}:
                esperado = formatar_preco(projeto.preco_centavos)
                for l, txt, c in encontrados:
                    achados.append({
                        "tipo": "preco_divergente", "titulo": "Preço diferente do briefing",
                        "descricao": f"Na arte: R$ {txt}. No briefing: R$ {esperado}.",
                        "regiao": _regiao(l, W, H), "referencia": _pagina_ref(projeto, "preco"),
                        "sugestao": {"de": txt, "para": esperado,
                                     "linha_original": l.texto,
                                     "linha_corrigida": l.texto.replace(txt, esperado)},
                    })

    # ---------- 2) ORTOGRAFIA ----------
    try:
        erros = await ortografia.verificar_linhas([l.texto for l in linhas])
        aplicadas.append("ortografia")
        ignorar = _palavras_ignoradas(projeto)
        por_linha: dict[int, list] = {}
        for e in erros:
            if e.palavra.lower() in ignorar or any(ch.isdigit() for ch in e.palavra):
                continue
            por_linha.setdefault(e.linha, []).append(e)
        for idx, lista in sorted(por_linha.items()):
            l = linhas[idx]
            corrigida, pares = l.texto, []
            for e in sorted(lista, key=lambda x: -x.inicio):  # de trás p/ frente mantém os offsets
                if e.sugestoes:
                    corrigida = corrigida[:e.inicio] + e.sugestoes[0] + corrigida[e.inicio + e.tamanho:]
                    pares.append({"de": e.palavra, "para": e.sugestoes[0]})
            pares.reverse()
            acento = bool(pares) and all(_sem_acento(p["de"]) == _sem_acento(p["para"]) for p in pares)
            achados.append({
                "tipo": "erro_escrita", "titulo": "Possível erro de escrita",
                "descricao": "Confira a acentuação da chamada." if acento else "Confira a grafia do texto.",
                "regiao": _regiao(l, W, H), "referencia": None,
                "sugestao": ({"de": ", ".join(p["de"] for p in pares), "para": ", ".join(p["para"] for p in pares),
                              "pares": pares, "linha_original": l.texto, "linha_corrigida": corrigida}
                             if pares else {"de": ", ".join(e.palavra for e in lista), "para": None,
                                            "pares": [], "linha_original": l.texto, "linha_corrigida": None}),
            })
    except ErroNegocio as exc:
        notas.append(f"Ortografia: não foi possível verificar ({exc.mensagem})")

    # ---------- 3) MARGEM ----------
    aplicadas.append("margem")
    minimo = settings.margem_minima_pct * min(W, H)
    obrigatoria = _norm(projeto.informacoes_obrigatorias or "")
    for l in linhas:
        dist = min(l.x, l.y, W - (l.x + l.w), H - (l.y + l.h))
        if dist < minimo:
            e_obrigatoria = bool(obrigatoria) and difflib.SequenceMatcher(
                None, _norm(l.texto), obrigatoria).ratio() >= 0.8
            achados.append({
                "tipo": "texto_na_borda", "titulo": "Texto muito próximo da borda",
                "descricao": ("Reposicione a informação obrigatória para manter uma margem de leitura."
                              if e_obrigatoria else
                              "Reposicione o texto para manter uma margem de leitura."),
                "regiao": _regiao(l, W, H), "referencia": None, "sugestao": None,
            })

    if projeto.prazo is None:
        notas.append("Prazo: Não foi possível confirmar.")

    analise = Analise(
        versao_id=versao.id, estado="concluida", verificacoes_aplicadas=aplicadas, notas=notas,
        linhas_ocr=[{"texto": l.texto, "x": l.x, "y": l.y, "w": l.w, "h": l.h,
                     "confianca": round(l.confianca, 3)} for l in linhas],
    )
    db.add(analise)
    db.flush()
    ordem = {"preco_divergente": 0, "erro_escrita": 1, "texto_na_borda": 2}
    for i, a in enumerate(sorted(achados, key=lambda a: ordem[a["tipo"]])):
        db.add(Achado(analise_id=analise.id, ordem=i, **a))
    db.commit()
    return analise


def _sem_acento(s: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


async def executar_analise_em_background(versao_id: int) -> None:
    """Roda depois da resposta HTTP (o front mostra 'Estamos conferindo sua arte...' e consulta o status)."""
    db = SessionLocal()
    try:
        versao = db.get(VersaoArte, versao_id)
        arte: Arte = versao.arte
        try:
            analise = await analisar_versao(db, versao, arte.projeto)
            pendentes = any(a.decisao == "pendente" for a in analise.achados)
            if arte.status == "em_analise":
                arte.status = "precisa_ajustes" if pendentes else "em_producao"
        except Exception as exc:  # não derruba o fluxo: registra e libera a pessoa para seguir
            log.exception("Falha na conferência automática da versão %s", versao_id)
            db.rollback()
            db.add(Analise(versao_id=versao_id, estado="erro",
                           erro=getattr(exc, "mensagem", str(exc)), verificacoes_aplicadas=[], notas=[]))
            versao = db.get(VersaoArte, versao_id)
            if versao.arte.status == "em_analise":
                versao.arte.status = "em_producao"
        db.commit()
    finally:
        db.close()