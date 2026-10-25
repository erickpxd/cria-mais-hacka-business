from typing import Literal

from pydantic import BaseModel, Field


class AnaliseVisao(BaseModel):
    """Formato que o modelo de visão é OBRIGADO a devolver (JSON Schema no Ollama)."""

    aprovado: bool
    categoria: Literal["produto", "pessoa", "documento", "paisagem", "outro"]
    motivos: list[str] = Field(default_factory=list)


class ResultadoAnalise(BaseModel):
    """Formato da resposta da API para o front-end."""

    filename: str | None = None
    aprovado: bool
    etapa: Literal["tecnica", "visao"]
    categoria: str | None = None
    motivos: list[str] = Field(default_factory=list)
    # Preenchidos só quando o outpainting foi usado:
    outpainting_aplicado: bool = False
    imagem_final_base64: str | None = None  # PNG já estendido, em base64


class Saude(BaseModel):
    api: bool = True
    ollama: bool
    modelo_visao_disponivel: bool
    outpainting_ativo: bool = False
    iopaint: bool | None = None  # None = outpainting desligado