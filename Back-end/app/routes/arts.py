import io

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import exigir_criador, usuario_atual
from app.domain import StatusArte, transicionar
from app.models import Analise, Arte, Comentario, EventoDecisao, Projeto, VersaoArte, agora
from app.serializers import ser_analise, ser_arte, ser_historico_arte, ser_versao, versao_atual
from app.services import analyses, armazenamento, templates
from app.services.briefing import parse_preco
from app.services.erros import ErroNegocio
from app.services.formatos import FORMATOS

router = APIRouter()


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
            if largura * altura > settings.max_pixels_arte:
                raise ErroNegocio(413, "A imagem excede o limite seguro de pixels.")
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
            status=StatusArte.EM_ANALISE.value,
        )
        db.add(arte)
        db.flush()
    else:
        arte.status = transicionar(arte.status, StatusArte.EM_ANALISE)
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
    db.flush()
    db.add(Analise(versao_id=versao.id, estado="queued", verificacoes_aplicadas=[], notas=[]))
    db.commit()
    db.refresh(versao)
    db.refresh(arte, attribute_names=["versoes"])
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
    exigir_criador(usuario)
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
    exigir_criador(usuario)
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
    resultado["historico"] = ser_historico_arte(arte)
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


@router.post("/artes/{arte_id}/analise", status_code=202)
def iniciar_analise(
    arte_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual),
):
    """Agenda a conferência real da versão atual, inclusive para templates antigos."""
    arte = _arte(db, arte_id)
    atual = versao_atual(arte)
    if not atual:
        raise ErroNegocio(409, "A arte ainda não possui uma versão para analisar.")
    if atual.analise and atual.analise.estado in ("queued", "processing"):
        return ser_analise(atual.analise)
    if atual.analise is None:
        db.add(Analise(
            versao_id=atual.id,
            estado="queued",
            verificacoes_aplicadas=[],
            notas=[],
        ))
    else:
        atual.analise.estado = "queued"
        atual.analise.erro = None
        atual.analise.verificacoes_aplicadas = []
        atual.analise.notas = []
    db.commit()
    db.refresh(atual)
    background_tasks.add_task(analyses.executar_analise_em_background, atual.id)
    return ser_analise(atual.analise)


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


@router.post("/artes/{arte_id}/correcoes", status_code=501)
def aplicar_correcoes(
    arte_id: int,
    corpo: CorrecoesIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual),
):
    raise ErroNegocio(501, "Correção automática de PNG/JPG não é suportada. Use um template editável.")


@router.post("/artes/{arte_id}/enviar-aprovacao")
def enviar_aprovacao(
    arte_id: int,
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual),
):
    exigir_criador(usuario)
    arte = _arte(db, arte_id)
    if arte.status not in (StatusArte.EM_PRODUCAO.value, StatusArte.PRECISA_DE_AJUSTES.value):
        raise ErroNegocio(409, "A arte ainda não pode ser enviada para aprovação.")
    arte.status = transicionar(arte.status, StatusArte.AGUARDANDO_APROVACAO)
    arte.enviada_em = agora()
    db.add(EventoDecisao(tipo="arte_enviada_aprovacao", usuario=usuario["id"],
                         payload={"arte_id": arte.id, "versao": versao_atual(arte).numero}))
    db.commit()
    return {"mensagem": "Arte enviada para aprovação.", "arte": ser_arte(arte)}


class AdaptarIn(BaseModel):
    canal: str


@router.post("/artes/{arte_id}/adaptar", status_code=501)
async def adaptar(
    arte_id: int,
    corpo: AdaptarIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual),
):
    raise ErroNegocio(501, "Adaptação confiável exige template editável e ainda não está disponível.")


class TemplateDadosIn(BaseModel):
    produto: str = Field(min_length=1, max_length=300)
    preco: str | None = None
    objetivo: str = Field(default="", max_length=1000)
    informacoes_obrigatorias: str = Field(default="", max_length=2000)


def _dados_template(corpo: TemplateDadosIn) -> dict:
    preco = parse_preco(corpo.preco)
    if corpo.preco and preco is None:
        raise ErroNegocio(422, "Preço inválido. Use o formato 17,90.")
    return {"produto": corpo.produto.strip(), "preco_centavos": preco,
            "objetivo": corpo.objetivo.strip(),
            "informacoes_obrigatorias": corpo.informacoes_obrigatorias.strip()}


def _template_editavel(arte: Arte) -> VersaoArte:
    atual = versao_atual(arte)
    if not atual or not atual.template_dados:
        raise ErroNegocio(409, "Esta arte não foi criada por um template editável.")
    return atual


@router.post("/artes/{arte_id}/template/preview")
def preview_template(
    arte_id: int,
    corpo: TemplateDadosIn,
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual),
):
    exigir_criador(usuario)
    arte = _arte(db, arte_id)
    _template_editavel(arte)
    png = templates.renderizar(arte.projeto, arte.canal, _dados_template(corpo))
    return StreamingResponse(io.BytesIO(png), media_type="image/png",
                             headers={"Cache-Control": "no-store"})


@router.post("/artes/{arte_id}/template/versoes", status_code=201)
def salvar_template(
    arte_id: int,
    corpo: TemplateDadosIn,
    db: Session = Depends(get_db),
    usuario: dict = Depends(usuario_atual),
):
    exigir_criador(usuario)
    arte = _arte(db, arte_id)
    atual = _template_editavel(arte)
    if arte.status == StatusArte.AGUARDANDO_APROVACAO.value:
        raise ErroNegocio(409, "Retire a arte da revisão antes de editar o template.")
    dados = _dados_template(corpo)
    png = templates.renderizar(arte.projeto, arte.canal, dados)
    numero = atual.numero + 1
    caminho = armazenamento.salvar(f"artes/{arte.id}", f"v{numero}.png", png)
    db.add(VersaoArte(
        arte_id=arte.id, numero=numero, arquivo=caminho,
        largura=atual.largura, altura=atual.altura, origem="template",
        nota="Campos editáveis atualizados pelo criador.", template_dados=dados,
        criado_por=usuario["id"],
    ))
    if arte.status in (StatusArte.APROVADA.value, StatusArte.PRECISA_DE_AJUSTES.value):
        arte.status = transicionar(arte.status, StatusArte.EM_ANALISE)
        arte.status = transicionar(arte.status, StatusArte.EM_PRODUCAO)
    db.add(EventoDecisao(tipo="template_editado", usuario=usuario["id"],
                         payload={"arte_id": arte.id, "versao": numero}))
    db.commit()
    db.refresh(arte, attribute_names=["versoes"])
    return ser_arte(arte)


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
