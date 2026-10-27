"""Conferência automática de uma versão da arte.

Verificações (regras + OCR, sem IA generativa):
  1. preço da arte x preço do briefing
  2. ortografia dos textos da arte (LanguageTool local)
  3. identidade Pague Menos: paleta, presença e posição do logo
  4. informação obrigatória e margem segura
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
from app.domain import StatusArte, transicionar
from app.models import Achado, Analise, Arte, Projeto, VersaoArte, agora
from app.services import armazenamento, ocr, ortografia
from app.services.briefing import RE_PRECO, formatar_preco
from app.services.erros import ErroNegocio

log = logging.getLogger(__name__)

CORES_PAGUE_MENOS = {
    "azul": np.array([18, 56, 166], dtype=np.int16),
    "vermelho": np.array([237, 28, 46], dtype=np.int16),
}
TOLERANCIA_COR = 58
PRESENCA_MINIMA_COR = 0.012


def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower()).strip()


def _regiao(l: ocr.LinhaTexto, W: int, H: int) -> dict:
    return {"x": l.x, "y": l.y, "w": l.w, "h": l.h,
            "nx": l.x / W, "ny": l.y / H, "nw": l.w / W, "nh": l.h / H,
            "largura_imagem": W, "altura_imagem": H}


def _palavras_ignoradas(projeto: Projeto) -> set[str]:
    base = " ".join(filter(None, [projeto.nome, projeto.produto, projeto.informacoes_obrigatorias,
                                  projeto.orientacoes, "Pague Menos Cria Mais CriaMais",
                                  " ".join(settings.ortografia_ignorar)]))
    return {w for w in re.findall(r"\w+", base.lower()) if len(w) >= 3}


def _pagina_ref(projeto: Projeto, chave: str) -> str | None:
    campo = (projeto.briefing_campos or {}).get(chave) or {}
    if campo.get("pagina"):
        return f"briefing, página {campo['pagina']}"
    return "briefing" if projeto.briefing_arquivo else None


def _percentual_cor(img_bgr: np.ndarray, rgb: np.ndarray) -> float:
    imagem_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype(np.int16)
    distancia = np.linalg.norm(imagem_rgb - rgb, axis=2)
    return float(np.mean(distancia <= TOLERANCIA_COR))


def _achados_de_identidade(img: np.ndarray, linhas: list[ocr.LinhaTexto], W: int, H: int) -> list[dict]:
    """Aplica regras determinísticas da POC; não declara conformidade oficial da marca."""
    achados: list[dict] = []
    percentuais = {nome: _percentual_cor(img, rgb) for nome, rgb in CORES_PAGUE_MENOS.items()}
    for nome, percentual in percentuais.items():
        if percentual < PRESENCA_MINIMA_COR:
            achados.append({
                "tipo": "cor_institucional_ausente",
                "titulo": f"{nome.capitalize()} institucional pouco presente",
                "descricao": (
                    f"Aproximadamente {percentual:.1%} da arte está próxima do {nome} configurado. "
                    "Revise a paleta antes de enviar para aprovação."
                ),
                "regiao": None,
                "referencia": "Guia de marca Pague Menos configurado na POC",
                "sugestao": {
                    "de": f"{percentual:.1%} detectado",
                    "para": f"usar {nome} Pague Menos nos elementos de marca",
                    "confianca": 1.0,
                },
            })

    linhas_logo = [linha for linha in linhas if "pague menos" in _norm(linha.texto)]
    if not linhas_logo:
        achados.append({
            "tipo": "logo_nao_localizado",
            "titulo": "Logo Pague Menos não localizado",
            "descricao": (
                "O OCR não localizou a assinatura “Pague Menos”. Confirme visualmente e inclua o logo "
                "oficial se ele estiver ausente."
            ),
            "regiao": None,
            "referencia": "Guia de marca Pague Menos configurado na POC",
            "sugestao": {
                "de": "não localizado pelo OCR",
                "para": "logo visível na faixa superior e dentro da margem segura",
                "confianca": 0.65,
            },
        })
    else:
        logo = max(linhas_logo, key=lambda linha: linha.confianca)
        margem = min(logo.x, logo.y, W - logo.x - logo.w, H - logo.y - logo.h)
        if logo.y / H > 0.30 or margem < settings.margem_minima_pct * min(W, H):
            achados.append({
                "tipo": "logo_fora_da_area",
                "titulo": "Logo fora da área recomendada",
                "descricao": "Reposicione o logo na faixa superior, preservando a margem segura da peça.",
                "regiao": _regiao(logo, W, H),
                "referencia": "Guia de marca Pague Menos configurado na POC",
                "sugestao": {
                    "de": "posição atual",
                    "para": "faixa superior com margem segura",
                    "confianca": round(logo.confianca, 3),
                },
            })
    return achados


def _informacao_obrigatoria_ausente(
    projeto: Projeto, linhas: list[ocr.LinhaTexto]
) -> dict | None:
    esperada = _norm(projeto.informacoes_obrigatorias or "")
    if not esperada:
        return None
    observado = _norm(" ".join(linha.texto for linha in linhas))
    tokens = set(esperada.split())
    cobertura = len(tokens & set(observado.split())) / max(1, len(tokens))
    if esperada in observado or cobertura >= 0.7:
        return None
    return {
        "tipo": "informacao_obrigatoria_ausente",
        "titulo": "Informação obrigatória não confirmada",
        "descricao": "O texto exigido pelo briefing não foi localizado integralmente na arte.",
        "regiao": None,
        "referencia": _pagina_ref(projeto, "informacoes_obrigatorias"),
        "sugestao": {
            "de": f"{cobertura:.0%} do texto reconhecido",
            "para": projeto.informacoes_obrigatorias,
            "confianca": 0.65,
        },
    }


async def analisar_versao(db: Session, versao: VersaoArte, projeto: Projeto) -> Analise:
    analise = versao.analise or Analise(versao_id=versao.id)
    if versao.analise:
        for achado in list(analise.achados):
            db.delete(achado)
    else:
        db.add(analise)
    analise.estado = "processing"
    analise.erro = None
    analise.engine_version = "paddleocr-local+brand-rules-v1"
    analise.verificacoes_aplicadas = []
    analise.notas = []
    analise.linhas_ocr = []
    analise.iniciada_em = agora()
    analise.finalizada_em = None
    db.commit()

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

    # ---------- IDENTIDADE DE MARCA ----------
    achados.extend(_achados_de_identidade(img, linhas, W, H))
    aplicadas.extend(["paleta_pague_menos", "logo_pague_menos"])

    obrigatoria_ausente = _informacao_obrigatoria_ausente(projeto, linhas)
    if obrigatoria_ausente:
        achados.append(obrigatoria_ausente)
    aplicadas.append("informacao_obrigatoria")

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
                                     "confianca": round(l.confianca, 3),
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
                              "pares": pares, "confianca": round(l.confianca, 3),
                              "linha_original": l.texto, "linha_corrigida": corrigida}
                             if pares else {"de": ", ".join(e.palavra for e in lista), "para": None,
                                            "pares": [], "confianca": round(l.confianca, 3),
                                            "linha_original": l.texto, "linha_corrigida": None}),
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
    notas.append(
        "Tipografia: PNG/JPG não informa a família da fonte. A POC confere legibilidade, "
        "margens e texto; a fonte exata exige arquivo editável ou referência tipográfica cadastrada."
    )

    analise.estado = "completed"
    analise.verificacoes_aplicadas = aplicadas
    analise.notas = notas
    analise.linhas_ocr = [{"texto": l.texto, "x": l.x, "y": l.y, "w": l.w, "h": l.h,
                           "confianca": round(l.confianca, 3)} for l in linhas]
    analise.finalizada_em = agora()
    db.flush()
    ordem = {
        "logo_nao_localizado": 0,
        "logo_fora_da_area": 1,
        "cor_institucional_ausente": 2,
        "informacao_obrigatoria_ausente": 3,
        "preco_divergente": 4,
        "erro_escrita": 5,
        "texto_na_borda": 6,
    }
    for i, a in enumerate(sorted(achados, key=lambda a: ordem.get(a["tipo"], 99))):
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
                arte.status = transicionar(arte.status, StatusArte.PRECISA_DE_AJUSTES if pendentes else StatusArte.EM_PRODUCAO)
        except Exception as exc:  # não derruba o fluxo: registra e libera a pessoa para seguir
            log.exception("Falha na conferência automática da versão %s", versao_id)
            db.rollback()
            versao = db.get(VersaoArte, versao_id)
            analise = versao.analise or Analise(versao_id=versao_id)
            analise.estado = "failed"
            analise.erro = getattr(exc, "mensagem", str(exc))
            analise.verificacoes_aplicadas = []
            analise.notas = []
            analise.finalizada_em = agora()
            db.add(analise)
            if versao.arte.status == "em_analise":
                versao.arte.status = "em_producao"
        db.commit()
    finally:
        db.close()
