"""Arquivos em disco (volume /data). O banco guarda só o caminho relativo."""
import uuid
from pathlib import Path

from app.config import settings


def raiz() -> Path:
    p = Path(settings.data_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def salvar(subpasta: str, nome_arquivo: str, conteudo: bytes) -> str:
    destino = raiz() / subpasta
    destino.mkdir(parents=True, exist_ok=True)
    (destino / nome_arquivo).write_bytes(conteudo)
    return f"{subpasta}/{nome_arquivo}"


def novo_nome(extensao: str) -> str:
    return f"{uuid.uuid4().hex}{extensao}"


def caminho(relativo: str) -> Path:
    c = (raiz() / relativo).resolve()
    if not str(c).startswith(str(raiz().resolve())):
        raise ValueError("Caminho inválido.")
    return c


def ler(relativo: str) -> bytes:
    return caminho(relativo).read_bytes()