from enum import StrEnum

from app.services.erros import ErroNegocio


class StatusArte(StrEnum):
    EM_ANALISE = "em_analise"
    EM_PRODUCAO = "em_producao"
    PRECISA_DE_AJUSTES = "precisa_de_ajustes"
    AGUARDANDO_APROVACAO = "aguardando_aprovacao"
    APROVADA = "aprovada"


TRANSICOES: dict[StatusArte, set[StatusArte]] = {
    StatusArte.EM_ANALISE: {StatusArte.EM_PRODUCAO, StatusArte.PRECISA_DE_AJUSTES},
    StatusArte.EM_PRODUCAO: {StatusArte.AGUARDANDO_APROVACAO},
    StatusArte.PRECISA_DE_AJUSTES: {StatusArte.EM_ANALISE, StatusArte.AGUARDANDO_APROVACAO},
    StatusArte.AGUARDANDO_APROVACAO: {StatusArte.APROVADA, StatusArte.PRECISA_DE_AJUSTES},
    StatusArte.APROVADA: {StatusArte.EM_ANALISE},
}


def transicionar(atual: str, destino: StatusArte) -> str:
    try:
        origem = StatusArte(atual)
    except ValueError as exc:
        raise ErroNegocio(409, f"Estado desconhecido da arte: {atual}") from exc
    if destino not in TRANSICOES.get(origem, set()):
        raise ErroNegocio(409, f"Transição inválida: {origem.value} → {destino.value}.")
    return destino.value
