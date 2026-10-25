"""Adapta uma arte para outro canal: estende o fundo (outpainting) até a proporção do formato
e redimensiona para a medida exata. NÃO reorganiza elementos da arte (isso exigiria layout editável)."""
import asyncio
import io

from PIL import Image

from app.config import settings
from app.services import outpainting
from app.services.erros import ErroNegocio
from app.services.formatos import FORMATOS


def _redimensionar(png: bytes, tamanho: tuple[int, int]) -> bytes:
    with Image.open(io.BytesIO(png)) as im:
        im = im.convert("RGB")
        if im.size != tamanho:
            im = im.resize(tamanho, Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()


async def adaptar(contents: bytes, canal: str) -> tuple[bytes, str]:
    """Devolve (png_final, nota_da_versao)."""
    fmt = FORMATOS.get(canal)
    if not fmt:
        raise ErroNegocio(422, f"Canal desconhecido: {canal}")
    estendida = await outpainting.expandir_imagem(contents, proporcao=(fmt["largura"], fmt["altura"]))
    final = await asyncio.to_thread(_redimensionar, estendida, (fmt["largura"], fmt["altura"]))
    metodo = ("fundo estendido pelo IOPaint" if settings.outpainting_ativo
              else "fundo estendido por replicação de borda (IOPaint desligado)")
    return final, f"Adaptada para {fmt['nome']} ({fmt['largura']}×{fmt['altura']}): {metodo}. Original preservada."