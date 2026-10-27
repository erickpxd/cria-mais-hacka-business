import base64
import io
import logging
import math

import httpx
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

log = logging.getLogger(__name__)



class ErroOutpainting(Exception):
    """Erro controlado durante a expansão da imagem."""

    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem

def _abrir_imagem(contents : bytes) -> Image.Image:
    """Decodifica os bytes e devolve uma imagem RGB válida."""

    try:
         with Image.open(io.BytesIO(contents)) as imagem:
            imagem.load()
            return ImageOps.exif_transpose(imagem).convert("RGB")
         
    except(UnidentifiedImageError, OSError, ValueError) as exc:
         raise ErroOutpainting(
            400, "O arquivo recebido não é uma imagem válida."
        ) from exc



def _preparar_canvas(
    imagem: Image.Image,
    proporcao: tuple[int, int] | None = None,
) -> tuple[Image.Image, Image.Image, int, int]:
    """
    Cria a tela expandida e a máscara.

    Máscara preta: imagem original.
    Máscara branca: regiões externas que o IOPaint preencherá.
    """
    largura, altura = imagem.size

    largura_alvo, altura_alvo = proporcao or (
        settings.proporcao_largura,
        settings.proporcao_altura,
    )
    proporcao_alvo = largura_alvo / altura_alvo

    if proporcao_alvo <= 0:
        raise ErroOutpainting(500, "A proporção configurada é inválida.")

    # Se a proporção já estiver dentro da tolerância, não expandimos.
    proporcao_atual = largura / altura
    if abs(proporcao_atual - proporcao_alvo) <= settings.tolerancia_proporcao:
        return imagem, None, 0, 0

    # Aumenta somente uma dimensão, sem reduzir nem cortar a original.
    if proporcao_atual < proporcao_alvo:
        nova_largura = math.ceil(altura * proporcao_alvo)
        nova_altura = altura
    else:
        nova_largura = largura
        nova_altura = math.ceil(largura / proporcao_alvo)

    esquerda = (nova_largura - largura) // 2
    direita = nova_largura - largura - esquerda
    topo = (nova_altura - altura) // 2
    base = nova_altura - altura - topo

    # Estende provisoriamente os pixels das bordas.
    pixels = np.asarray(imagem)
    pixels_expandidos = np.pad(
        pixels,
        ((topo, base), (esquerda, direita), (0, 0)),
        mode="edge",
    )
    canvas = Image.fromarray(pixels_expandidos.astype(np.uint8))

    # Preto = original; branco = áreas que a IA deve preencher.
    mascara = Image.new("L", (nova_largura, nova_altura), 255)
    mascara.paste(0, (esquerda, topo, esquerda + largura, topo + altura))

    return canvas, mascara, esquerda, topo



def _para_base64(imagem: Image.Image) -> str:
    """Codifica uma imagem PNG em base64."""
    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")



def _validar_bytes_imagem(contents: bytes) -> Image.Image:
    """Confirma que a resposta contém uma imagem decodificável."""
    try:
        with Image.open(io.BytesIO(contents)) as imagem:
            imagem.load()
            return imagem.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ErroOutpainting(
            502, "O IOPaint não retornou uma imagem válida."
        ) from exc



async def expandir_imagem(contents: bytes, proporcao: tuple[int, int] | None = None) -> bytes:
    """Expande a imagem usando o serviço IOPaint."""
    imagem_original = _abrir_imagem(contents)
    canvas, mascara, x, y = _preparar_canvas(imagem_original, proporcao)

    # Nenhuma expansão necessária.
    if mascara is None:
        return contents

    if not settings.outpainting_ativo:
        buffer = io.BytesIO()
        canvas.save(buffer, format="PNG")
        return buffer.getvalue()

    payload = {
        "image": _para_base64(canvas),
        "mask": _para_base64(mascara),
        "prompt": "Continue naturalmente o cenário ao redor da imagem.",
        "negative_prompt": "deformações, artefatos, baixa qualidade",
    }

    url = f"{settings.iopaint_url.rstrip('/')}/api/v1/inpaint"

    try:
        async with httpx.AsyncClient(
            timeout=settings.iopaint_timeout
        ) as client:
            resposta = await client.post(url, json=payload)
            resposta.raise_for_status()

    except httpx.TimeoutException as exc:
        raise ErroOutpainting(
            504, "O IOPaint demorou demais para responder."
        ) from exc

    except httpx.HTTPStatusError as exc:
        log.warning(
            "IOPaint retornou status HTTP %s.",
            exc.response.status_code,
        )
        raise ErroOutpainting(
            502, "O IOPaint rejeitou a requisição."
        ) from exc

    except httpx.RequestError as exc:
        log.warning("Não foi possível conectar ao IOPaint.")
        raise ErroOutpainting(
            503, "O serviço IOPaint está indisponível."
        ) from exc

    imagem_gerada = _validar_bytes_imagem(resposta.content)

    if imagem_gerada.size != canvas.size:
        raise ErroOutpainting(
            502, "O IOPaint retornou dimensões inesperadas."
        )

    # Recoloca os pixels originais para garantir sua preservação.
    imagem_gerada.paste(imagem_original, (x, y))

    buffer = io.BytesIO()
    imagem_gerada.save(buffer, format="PNG")
    return buffer.getvalue()
