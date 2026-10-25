import json
import re
import shutil
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import usuario_atual
from app.models import Arte, EventoDecisao, Projeto
from app.serializers import ser_formatos, ser_projeto_detalhe, ser_projeto_resumo
from app.services import armazenamento, briefing
from app.services.erros import ErroNegocio
from app.services.formatos import FORMATOS

router = APIRouter(prefix="/api")
TOKEN = re.compile(r"^[0-9a-f]{32}$")


class ProjetoIn(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    objetivo: str | None = None
    descricao: str | None = None
    prazo: date | None = None
    produto: str | None = None
    preco: str | None = None            # "R$ 17,90" ou "17,90"
    informacoes_obrigatorias: str | None = None
    orientacoes: str | None = None
    canais: list[str] = []
    briefing_token: str | None = None   # vem de /api/briefings/extrair


@router.get("/me")
def me(usuario: dict = Depends(usuario_atual), db: Session = Depends(get_db)):
    n = db.scalar(select(func.count()).select_from(Arte).where(Arte.status == "aguardando_aprovacao"))
    return {**usuario, "aprovacoes_pendentes": n or 0}


@router.get("/formatos")
def formatos():
    return ser_formatos()


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), usuario: dict = Depends(usuario_atual)):
    projetos = db.scalars(select(Projeto).order_by(Projeto.atualizado_em.desc())).all()
    resumos = [ser_projeto_resumo(p) for p in projetos]
    return {
        "atencao": {
            "artes_com_ajustes": sum(r["artes_com_ajustes"] for r in resumos),
            "artes_aguardando_aprovacao": sum(r["artes_aguardando"] for r in resumos),
            "campanhas_com_formato_pendente": sum(1 for r in resumos if r["formatos"]["faltantes"]),
        },
        "projetos_recentes": resumos[:3],
    }


@router.get("/projetos")
def listar(db: Session = Depends(get_db), usuario: dict = Depends(usuario_atual)):
    return [ser_projeto_resumo(p) for p in db.scalars(select(Projeto).order_by(Projeto.atualizado_em.desc()))]


@router.get("/projetos/{projeto_id}")
def detalhe(projeto_id: int, status: str | None = None, canal: str | None = None,
            db: Session = Depends(get_db), usuario: dict = Depends(usuario_atual)):
    p = db.get(Projeto, projeto_id)
    if not p:
        raise HTTPException(404, "Projeto não encontrado.")
    d = ser_projeto_detalhe(p)
    if status:
        d["artes"] = [a for a in d["artes"] if a["status"] == status]
    if canal:
        d["artes"] = [a for a in d["artes"] if a["canal"] == canal]
    return d


@router.post("/briefings/extrair")
async def extrair_briefing(file: UploadFile = File(...), usuario: dict = Depends(usuario_atual)):
    nome = file.filename or "briefing"
    ext = "." + nome.rsplit(".", 1)[-1].lower() if "." in nome else ""
    if ext not in settings.extensoes_briefing:
        # mensagem do design: "Envie um arquivo PDF, DOCX ou TXT."
        raise ErroNegocio(415, "Envie um arquivo PDF, DOCX ou TXT.")
    conteudo = await file.read(settings.max_briefing_bytes + 1)
    if len(conteudo) > settings.max_briefing_bytes:
        raise ErroNegocio(413, f"O arquivo passa de {settings.max_briefing_mb} MB.")
    if not conteudo:
        raise ErroNegocio(400, "O arquivo está vazio.")

    paginas, paginado = briefing.ler_paginas(nome, conteudo)
    campos = briefing.extrair_campos(paginas, paginado)
    avisos = briefing.avisos_do_briefing(campos, paginas)

    token = uuid.uuid4().hex
    armazenamento.salvar("tmp/briefings", f"{token}{ext}", conteudo)
    armazenamento.salvar("tmp/briefings", f"{token}.json", json.dumps(
        {"nome": nome, "ext": ext, "campos": campos}, ensure_ascii=False).encode())
    return {"token": token, "arquivo": nome, "total_paginas": len(paginas) if paginado else None,
            "campos": campos, "avisos": avisos}


@router.post("/projetos", status_code=201)
def criar(corpo: ProjetoIn, db: Session = Depends(get_db), usuario: dict = Depends(usuario_atual)):
    invalidos = [c for c in corpo.canais if c not in FORMATOS]
    if invalidos:
        raise ErroNegocio(422, f"Canais desconhecidos: {', '.join(invalidos)}")
    if corpo.preco and briefing.parse_preco(corpo.preco) is None:
        raise ErroNegocio(422, "Preço inválido. Use o formato 17,90.")

    p = Projeto(
        nome=corpo.nome.strip(), objetivo=corpo.objetivo, descricao=corpo.descricao, prazo=corpo.prazo,
        produto=corpo.produto, preco_centavos=briefing.parse_preco(corpo.preco),
        informacoes_obrigatorias=corpo.informacoes_obrigatorias, orientacoes=corpo.orientacoes,
        canais=corpo.canais, criado_por=usuario["id"],
    )
    db.add(p)
    db.flush()

    if corpo.briefing_token:
        if not TOKEN.match(corpo.briefing_token):
            raise ErroNegocio(400, "Token de briefing inválido.")
        meta_rel = f"tmp/briefings/{corpo.briefing_token}.json"
        try:
            meta = json.loads(armazenamento.ler(meta_rel))
            origem = armazenamento.caminho(f"tmp/briefings/{corpo.briefing_token}{meta['ext']}")
        except (FileNotFoundError, ValueError):
            raise ErroNegocio(404, "O briefing enviado expirou. Envie o arquivo novamente.")
        destino = f"briefings/{p.id}/{armazenamento.novo_nome(meta['ext'])}"
        armazenamento.caminho(destino).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(origem, armazenamento.caminho(destino))
        p.briefing_arquivo, p.briefing_nome, p.briefing_campos = destino, meta["nome"], meta["campos"]

    db.add(EventoDecisao(tipo="projeto_criado", usuario=usuario["id"],
                         payload={"projeto_id": p.id, "via_briefing": bool(corpo.briefing_token)}))
    db.commit()
    return ser_projeto_detalhe(p)


@router.get("/projetos/{projeto_id}/briefing")
def baixar_briefing(projeto_id: int, db: Session = Depends(get_db), usuario: dict = Depends(usuario_atual)):
    p = db.get(Projeto, projeto_id)
    if not p or not p.briefing_arquivo:
        raise HTTPException(404, "Este projeto não tem briefing anexado.")
    return FileResponse(armazenamento.caminho(p.briefing_arquivo), filename=p.briefing_nome)