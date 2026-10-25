class ErroNegocio(Exception):
    def __init__(self, status: int, mensagem: str):
        self.status = status
        self.mensagem = mensagem
        super().__init__(mensagem)


class ErroServicoIA(ErroNegocio):
    pass
