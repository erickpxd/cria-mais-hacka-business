class ErroNegocio(Exception):
    """Erro esperado, já com o status HTTP e a mensagem que o usuário deve ver."""

    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


class ErroServicoIA(ErroNegocio):
    """Falha ao falar com um serviço externo (Ollama, IOPaint, LanguageTool)."""