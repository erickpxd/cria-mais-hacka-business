from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base
from app.models import Arte, Projeto, VersaoArte
from app.services import analyses, ocr


class OCRFalso:
    def __init__(self, texto: str):
        self.texto = texto

    def ler(self, _imagem):
        return [ocr.LinhaTexto(self.texto, 100, 100, 120, 30, 0.99)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("texto", "divergencias"),
    [("Oferta R$ 19,90", 1), ("Oferta R$ 17,90", 0)],
)
async def test_preco_da_imagem_muda_o_resultado(tmp_path, monkeypatch, texto, divergencias):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    monkeypatch.setattr(ocr, "obter_motor", lambda: OCRFalso(texto))

    async def sem_erros(_linhas):
        return []

    monkeypatch.setattr(analyses.ortografia, "verificar_linhas", sem_erros)
    arquivo = Path(tmp_path, "arte.png")
    Image.new("RGB", (400, 400), "white").save(arquivo)
    with Session() as db:
        projeto = Projeto(nome="Teste", produto="Shampoo", preco_centavos=1790,
                          canais=["instagram_feed"], criado_por="ana")
        arte = Arte(projeto=projeto, nome="Arte", canal="instagram_feed",
                    status="em_analise", criado_por="ana")
        versao = VersaoArte(arte=arte, numero=1, arquivo="arte.png", largura=400, altura=400,
                            origem="upload", criado_por="ana")
        db.add_all([projeto, arte, versao])
        db.commit()
        resultado = await analyses.analisar_versao(db, versao, projeto)
        encontrados = [item for item in resultado.achados if item.tipo == "preco_divergente"]
        assert len(encontrados) == divergencias
        assert resultado.estado == "completed"

