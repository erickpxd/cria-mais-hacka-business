import asyncio
import logging
import time

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.schemas import ResultadoAnalise, Saude
from app.services import technician as tecnico, vision as visao

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


async def _ler_upload(file: UploadFile) -> bytes:
    """Valida tipo e tamanho ANTES de processar."""
    if file.content_type not in settings.tipos_aceitos:
        raise HTTPException(
            415, f"Tipo '{file.content_type}' não aceito. Use: {', '.join(settings.tipos_aceitos)}."
        )
    contents = await file.read(settings.max_upload_bytes + 1)
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(413, f"Arquivo maior que {settings.max_upload_mb} MB.")
    if not contents:
        raise HTTPException(400, "Arquivo vazio.")
    return contents


@router.get("/saude", response_model=Saude)
async def saude():
    ollama_ok, modelo_ok = await visao.verificar_ollama()
    return Saude(ollama=ollama_ok, modelo_visao_disponivel=modelo_ok)


@router.post("/analisar", response_model=ResultadoAnalise)
async def analisar(file: UploadFile = File(...)):
    inicio = time.perf_counter()
    contents = await _ler_upload(file)

    # OpenCV é CPU-bound: roda em thread para não travar o servidor
    img = await asyncio.to_thread(tecnico.decodificar, contents)
    if img is None:
        raise HTTPException(400, "O arquivo não é uma imagem válida.")

    # Etapa 1: filtro técnico (barato)
    problemas = await asyncio.to_thread(tecnico.checar_tecnico, img)
    if problemas:
        log.info("%s reprovada na etapa técnica (%.2fs)", file.filename, time.perf_counter() - inicio)
        return ResultadoAnalise(
            filename=file.filename, aprovado=False, etapa="tecnica", motivos=problemas
        )

    # Etapa 2: modelo de visão (caro)
    try:
        analise = await visao.analisar_imagem(contents)
    except visao.ErroServicoIA as e:
        raise HTTPException(e.status, e.mensagem)

    log.info(
        "%s -> aprovado=%s categoria=%s (%.2fs)",
        file.filename, analise.aprovado, analise.categoria, time.perf_counter() - inicio,
    )
    return ResultadoAnalise(
        filename=file.filename,
        aprovado=analise.aprovado,
        etapa="visao",
        categoria=analise.categoria,
        motivos=analise.motivos,
    )


# TODO (do seu CHANGE): decidir se esta rota continua. Se sim, o modelo é settings.modelo_ocr.
@router.post("/uploadHandwriting")
async def ler_manuscrito(file: UploadFile = File(...)):
    contents = await _ler_upload(file)
    try:
        texto = await visao.extrair_texto(contents)
    except visao.ErroServicoIA as e:
        raise HTTPException(e.status, e.mensagem)
    return {"filename": file.filename, "text": texto}