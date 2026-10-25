from fastapi import Header, HTTPException

from app.config import settings


def usuario_atual(x_usuario: str = Header(default="ana")) -> dict:
    """Autenticação de DEMONSTRAÇÃO: o front manda X-Usuario (ana, bruno, rafael)."""
    dados = settings.usuarios.get(x_usuario.lower())
    if not dados:
        raise HTTPException(401, "Usuário desconhecido.")
    return {"id": x_usuario.lower(), **dados}


def exigir_revisor(usuario: dict) -> None:
    if usuario["papel"] != "revisor":
        raise HTTPException(403, "Somente revisores podem decidir sobre a aprovação.")