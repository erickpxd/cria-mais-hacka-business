"""Toda a comunicação com o Ollama fica aqui. Trocar de modelo = mexer só neste arquivo/config."""
import logging

import httpx
from ollama import AsyncClient, ResponseError
from pydantic import ValidationError

from app.config import settings
from app.schemas import AnaliseVisao

log = logging.getLogger(__name__)

client = AsyncClient(host=settings.ollama_url, timeout=settings.ollama_timeout)


class ErroServicoIA(Exception):
    """Erro ao falar com o Ollama, já com o status HTTP que a API deve devolver."""

    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


async def _chat(**kwargs):
    try:
        return await client.chat(**kwargs)
    except httpx.TimeoutException:
        raise ErroServicoIA(504, "O modelo demorou demais para responder.")
    except ResponseError as e:
        if e.status_code == 404:
            raise ErroServicoIA(
                503,
                f"Modelo '{kwargs.get('model')}' não encontrado no Ollama. "
                "Aguarde o download terminar (docker compose logs ollama-init).",
            )
        raise ErroServicoIA(502, f"Erro do Ollama: {e.error}")
    except (ConnectionError, httpx.TransportError):
        raise ErroServicoIA(503, "Não foi possível conectar ao Ollama.")


def _montar_prompt() -> str:
    criterios = "\n".join(f"- {c}" for c in settings.criterios_visao)
    return (
        "Você é um verificador de imagens. Avalie a imagem segundo estes critérios:\n"
        f"{criterios}\n"
        "Aprove SOMENTE se TODOS os critérios forem atendidos. "
        "Responda apenas no formato JSON pedido. Em 'motivos', explique "
        "brevemente, em português, cada critério não atendido."
    )


async def analisar_imagem(contents: bytes) -> AnaliseVisao:
    resp = await _chat(
        model=settings.modelo_visao,
        messages=[{"role": "user", "content": _montar_prompt(), "images": [contents]}],
        format=AnaliseVisao.model_json_schema(),
        options={"temperature": 0},
    )
    bruto = resp["message"]["content"]
    try:
        return AnaliseVisao.model_validate_json(bruto)
    except ValidationError:
        log.error("Resposta fora do schema: %s", bruto)
        raise ErroServicoIA(502, "O modelo retornou uma resposta fora do formato esperado.")


async def extrair_texto(contents: bytes) -> str:
    resp = await _chat(
        model=settings.modelo_ocr,
        messages=[{
            "role": "user",
            "content": "Extract all text from this image and format it as JSON.",
            "images": [contents],
        }],
    )
    return resp["message"]["content"]


async def verificar_ollama() -> tuple[bool, bool]:
    """Devolve (ollama_no_ar, modelo_de_visao_baixado)."""
    try:
        lista = await client.list()
    except Exception:
        return False, False
    nomes = [m.model or "" for m in lista.models]
    return True, any(n.split(":")[0] == settings.modelo_visao.split(":")[0] for n in nomes)