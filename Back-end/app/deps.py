from fastapi import Header, HTTPException, Query

from app.config import settings


def usuario_atual(
    x_demo_user: str | None = Header(default=None, alias="X-Demo-User"),
    demo_user: str | None = Query(default=None, include_in_schema=False),
) -> dict:
    """Identidade de demonstração explícita. Isto não é autenticação de produção."""
    x_demo_user = x_demo_user or demo_user
    if not x_demo_user:
        raise HTTPException(401, "Informe X-Demo-User para usar o ambiente demonstrativo.")
    dados = settings.usuarios.get(x_demo_user.lower())
    if not dados:
        raise HTTPException(401, "Usuário desconhecido.")
    return {"id": x_demo_user.lower(), **dados}


def exigir_revisor(usuario: dict) -> None:
    if usuario["papel"] != "revisor":
        raise HTTPException(403, "Somente revisores podem decidir sobre a aprovação.")


def exigir_criador(usuario: dict) -> None:
    if usuario["papel"] != "designer":
        raise HTTPException(403, "Somente criadores podem alterar projetos e artes.")
