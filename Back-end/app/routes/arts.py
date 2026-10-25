import io

import cv2
import numpy as np
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import usuario_atual
from app.models import Arte, Comentario, EventoDecisao, Projeto, VersaoArte, agora
from app.serializers import ser_analise, ser_arte, ser_versao, versao_atual
from app.services import adaptations, analyses, armazenamento, corrections
from app.services.erros import ErroNegocio
from app.services.formatos import FORMATOS

router = APIRouter(prefix="/api")


def _arte(db: Session, arte_id: int) -> Arte:
    arte = db.get(Arte, arte_id)
    if not arte:
        raise HTTPException(404, "Arte não encontrada.")
    return arte


async def _imagem(file: UploadFile) -> tuple[bytes, int, int, str]:
    if file.content_type not in settings.tipos_arte:
        raise ErroNegocio(415, f"Tipo '{file.content_type}' não aceito.")
    conteudo = await file.read(settings.max_arte_bytes + 1)
    if len(conteudo) > settings.max_arte_bytes:
        raise ErroNegocio(413, f"O arquivo passa de {settings.max_arte_mb} MB.")
    if not conteudo:
        raise ErroNegocio(400, "O arquivo está vazio.")
    try:
        with Image.open(io.BytesIO(conteudo)) as imagem:
            largura, altura = imagem.size
            imagem.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ErroNegocio(400, "O arquivo não é uma imagem válida.") from exc
    extensao = ".jpg" if file.content_type == "image/jpeg" else f".{file.content_type.split('/')[-1]}"
    return conteudo, largura, altura, extensao


async def _criar_versao(
    projeto: Projeto,
    canal: str,
    file: UploadFile,
    usuario: dict,
    db: Session,
    background_tasks: BackgroundTasks,
    arte: Arte | None = None,
) -> Arte:
    if canal not in FORMATOS:
        raise ErroNegocio(422, f"Canal desconhecido: {canal}")
    conteudo, largura, altura, extensao = await _imagem(file)
    if arte is None:
        arte = Arte(
            projeto_id=projeto.id,
            nome=file.filename or "arte",
            canal=canal,
            criado_por=usuario["id"],
            status="em_analise",
            enviada_em=agora(),
        )
        db.add(arte)
        db.flush()
    else:
        arte.status = "em_analise"
    numero = max((v.numero for v in arte.versoes), default=0) + 1
    relativo = armazenamento.salvar(f"artes/{arte.id}", f"v{numero}{extensao}", conteudo)
    versao = VersaoArte(
        arte_id=arte.id,
        numero=numero,
        arquivo=relativo,
        largura=largura,
        altura=altura,
        origem="upload",
        criado_por=usuario["id"],
    )
    db.add(versao)
    db.commit()
    db.refresh(versao)
    background_tasks.add_task(analyses.executar_analise_em_background, versao.id)
    return arte


@router.post("/projetos/{projeto_id}/artes", status_code=201)
async def enviar(
    projeto_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    canal: str = "instagram_feed",
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual),
):
    projeto = db.get(Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado.")
    arte = await _criar_versao(projeto, canal, file, usuario, db, background_tasks)
    return ser_arte(arte)


@router.post("/artes/{arte_id}/versoes", status_code=201)
async def nova_versao(
    arte_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual),
):
    arte = _arte(db, arte_id)
    return ser_arte(await _criar_versao(
        arte.projeto, arte.canal, file, usuario, db, background_tasks, arte
    ))


@router.get("/artes/{arte_id}")
def detalhe(
    arte_id: int,
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual),
):
    arte = _arte(db, arte_id)
    atual = versao_atual(arte)
    resultado = ser_arte(arte)
    resultado["versoes"] = [ser_versao(v, v is atual) for v in arte.versoes]
    resultado["analise"] = ser_analise(atual.analise) if atual else None
    return resultado


@router.get("/artes/{arte_id}/analise")
def analise(
    arte_id: int,
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual),
):
    arte = _arte(db, arte_id)
    atual = versao_atual(arte)
    return ser_analise(atual.analise) if atual else None


@router.get("/artes/{arte_id}/versoes/{numero}/imagem")
def imagem(
    arte_id: int,
    numero: int,
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual),
):
    arte = _arte(db, arte_id)
    versao = next((v for v in arte.versoes if v.numero == numero), None)
    if not versao:
        raise HTTPException(404, "Versão não encontrada.")
    return FileResponse(armazenamento.caminho(versao.arquivo))


class CorrecoesIn(BaseModel):
    aceitos: list[int] = Field(default_factory=list)
    rejeitados: list[int] = Field(default_factory=list)


@router.post("/artes/{arte_id}/correcoes", status_code=201)
def aplicar_correcoes(
    arte_id: int,
    corpo: CorrecoesIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual),
):
    arte = _arte(db, arte_id)
    atual = versao_atual(arte)
    if not atual or not atual.analise:
        raise ErroNegocio(409, "A arte ainda não possui uma análise.")
    achados = {a.id: a for a in atual.analise.achados}
    selecionados = [achados.get(item_id) for item_id in corpo.aceitos]
    selecionados = [a for a in selecionados if a and a.sugestao and a.sugestao.get("linha_corrigida")]
    for achado_id in corpo.aceitos:
        if achado_id in achados:
            achados[achado_id].decisao = "aceito"
            achados[achado_id].decidido_por = usuario["id"]
            achados[achado_id].decidido_em = agora()
    for achado_id in corpo.rejeitados:
        if achado_id in achados:
            achados[achado_id].decisao = "rejeitado"
            achados[achado_id].decidido_por = usuario["id"]
            achados[achado_id].decidido_em = agora()
    if not selecionados:
        db.commit()
        return ser_arte(arte)
    imagem_bgr = cv2.imdecode(
        np.frombuffer(armazenamento.ler(atual.arquivo), np.uint8), cv2.IMREAD_COLOR
    )
    if imagem_bgr is None:
        raise ErroNegocio(400, "Não foi possível abrir a imagem da arte.")
    itens = [(a.regiao, a.sugestao["linha_corrigida"]) for a in selecionados if a.regiao]
    corrigida = corrections.aplicar_correcoes(imagem_bgr, itens)
    ok, png = cv2.imencode(".png", corrigida)
    if not ok:
        raise ErroNegocio(500, "Não foi possível gerar a versão corrigida.")
    numero = max(v.numero for v in arte.versoes) + 1
    relativo = armazenamento.salvar(f"artes/{arte.id}", f"v{numero}.png", png.tobytes())
    versao = VersaoArte(
        arte_id=arte.id, numero=numero, arquivo=relativo,
        largura=atual.largura, altura=atual.altura, origem="correcao",
        nota="Correções aceitas aplicadas.", criado_por=usuario["id"],
    )
    arte.status = "em_analise"
    db.add(versao)
    db.commit()
    db.refresh(versao)
    background_tasks.add_task(analyses.executar_analise_em_background, versao.id)
    return ser_arte(arte)


@router.post("/artes/{arte_id}/enviar-aprovacao")
def enviar_aprovacao(
    arte_id: int,
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual),
):
    arte = _arte(db, arte_id)
    if arte.status not in ("em_producao", "precisa_ajustes"):
        raise ErroNegocio(409, "A arte ainda não pode ser enviada para aprovação.")
    arte.status = "aguardando_aprovacao"
    arte.enviada_em = agora()
    db.add(EventoDecisao(tipo="arte_enviada_aprovacao", usuario=usuario["id"],
                         payload={"arte_id": arte.id, "versao": versao_atual(arte).numero}))
    db.commit()
    return {"mensagem": "Arte enviada para aprovação.", "arte": ser_arte(arte)}


class AdaptarIn(BaseModel):
    canal: str


@router.post("/artes/{arte_id}/adaptar", status_code=201)
async def adaptar(
    arte_id: int,
    corpo: AdaptarIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual),
):
    arte = _arte(db, arte_id)
    if corpo.canal not in FORMATOS:
        raise ErroNegocio(422, f"Canal desconhecido: {corpo.canal}")
    atual = versao_atual(arte)
    if not atual:
        raise ErroNegocio(409, "A arte não possui uma versão para adaptar.")
    conteudo, nota = await adaptations.adaptar(armazenamento.ler(atual.arquivo), corpo.canal)
    nova = Arte(
        projeto_id=arte.projeto_id, nome=arte.nome, canal=corpo.canal,
        status="em_analise", arte_origem_id=arte.id, criado_por=usuario["id"],
    )
    db.add(nova)
    db.flush()
    relativo = armazenamento.salvar(f"artes/{nova.id}", "v1.png", conteudo)
    formato = FORMATOS[corpo.canal]
    versao = VersaoArte(
        arte_id=nova.id, numero=1, arquivo=relativo, largura=formato["largura"],
        altura=formato["altura"], origem="adaptacao", nota=nota, criado_por=usuario["id"],
    )
    db.add(versao)
    db.commit()
    db.refresh(versao)
    background_tasks.add_task(analyses.executar_analise_em_background, versao.id)
    return ser_arte(nova)


class ComentarioIn(BaseModel):
    texto: str = Field(min_length=1)
    regiao: dict | None = None


@router.get("/artes/{arte_id}/comentarios")
def listar_comentarios(
    arte_id: int,
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual),
):
    arte = _arte(db, arte_id)
    return [{"id": c.id, "texto": c.texto, "regiao": c.regiao, "autor": c.autor,
             "versao": c.versao_numero, "criado_em": c.criado_em.isoformat()}
            for c in arte.comentarios]


@router.post("/artes/{arte_id}/comentarios", status_code=201)
def criar_comentario(
    arte_id: int,
    corpo: ComentarioIn,
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual),
):
    arte = _arte(db, arte_id)
    atual = versao_atual(arte)
    comentario = Comentario(
        arte_id=arte.id, versao_numero=atual.numero if atual else 1,
        autor=usuario["id"], texto=corpo.texto.strip(), regiao=corpo.regiao,
    )
    db.add(comentario)
    db.commit()
    db.refresh(comentario)
    return {"id": comentario.id, "texto": comentario.texto, "regiao": comentario.regiao,
            "autor": comentario.autor, "versao": comentario.versao_numero}