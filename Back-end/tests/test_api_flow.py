import io

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app.main import app
from app.models import Arte
from app.routes import arts


def test_fluxo_persistente_de_revisao(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def banco_teste():
        with TestSession() as session:
            yield session

    async def analise_controlada(_versao_id: int):
        return None

    app.dependency_overrides[get_db] = banco_teste
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    monkeypatch.setattr(arts.analyses, "executar_analise_em_background", analise_controlada)
    cliente = TestClient(app)
    criador = {"X-Demo-User": "ana"}
    revisor = {"X-Demo-User": "rafael"}

    try:
        assert cliente.get("/api/v1/me").status_code == 401
        assert cliente.post("/api/v1/projetos", headers=revisor,
                            json={"nome": "Não permitido"}).status_code == 403
        extracao = cliente.post(
            "/api/v1/briefings/extrair",
            headers=criador,
            files={"file": ("briefing.txt", b"CAMPANHA SINTETICA\nPRODUTO: Shampoo\nPRECO: R$ 17,90 ou R$ 19,90", "text/plain")},
        )
        assert extracao.status_code == 200
        assert extracao.json()["campos"]["preco"]["estado"] == "conflict"
        projeto = cliente.post(
            "/api/v1/projetos",
            headers=criador,
            json={
                "nome": "Campanha sintética",
                "objetivo": "Validar o fluxo",
                "produto": "Shampoo 400 ml",
                "preco": "R$ 17,90",
                "canais": ["instagram_feed", "instagram_stories"],
                "briefing_token": extracao.json()["token"],
            },
        )
        assert projeto.status_code == 201
        assert projeto.json()["tem_briefing"] is True

        imagem = io.BytesIO()
        Image.new("RGB", (400, 400), "white").save(imagem, format="PNG")
        envio = cliente.post(
            f"/api/v1/projetos/{projeto.json()['id']}/artes?canal=instagram_feed",
            headers=criador,
            files={"file": ("arte.png", imagem.getvalue(), "image/png")},
        )
        assert envio.status_code == 201
        arte_id = envio.json()["id"]
        assert cliente.post(
            f"/api/v1/projetos/{projeto.json()['id']}/artes?canal=instagram_feed",
            headers=revisor,
            files={"file": ("outra.png", imagem.getvalue(), "image/png")},
        ).status_code == 403
        assert cliente.post(
            f"/api/v1/projetos/{projeto.json()['id']}/artes?canal=instagram_feed",
            headers=criador,
            files={"file": ("script.svg", b"<svg/>", "image/svg+xml")},
        ).status_code == 415
        outro_projeto = cliente.post(
            "/api/v1/projetos", headers=criador,
            json={"nome": "Projeto isolado", "produto": "Outro", "canais": ["instagram_feed"]},
        )
        assert outro_projeto.status_code == 201
        assert cliente.get(
            f"/api/v1/projetos/{outro_projeto.json()['id']}", headers=criador
        ).json()["artes"] == []
        with TestSession.begin() as session:
            session.get(Arte, arte_id).status = "em_producao"

        assert cliente.post(f"/api/v1/artes/{arte_id}/aprovar", headers=revisor).status_code == 409
        assert cliente.get(f"/api/v1/artes/{arte_id}/exportar", headers=criador).status_code == 403
        assert cliente.post(
            f"/api/v1/artes/{arte_id}/enviar-aprovacao", headers=criador
        ).status_code == 200
        assert cliente.post(f"/api/v1/artes/{arte_id}/aprovar", headers=criador).status_code == 403
        assert cliente.post(
            f"/api/v1/artes/{arte_id}/solicitar-ajustes",
            headers=revisor,
            json={"comentario": "   "},
        ).status_code == 422
        assert cliente.post(
            f"/api/v1/artes/{arte_id}/solicitar-ajustes",
            headers=revisor,
            json={"comentario": "Aumentar o contraste."},
        ).status_code == 200

        nova = cliente.post(
            f"/api/v1/artes/{arte_id}/versoes",
            headers=criador,
            files={"file": ("arte-v2.png", imagem.getvalue(), "image/png")},
        )
        assert nova.status_code == 201
        assert nova.json()["versao_atual"] == 2
        detalhe = cliente.get(f"/api/v1/artes/{arte_id}", headers=criador).json()
        assert [versao["numero"] for versao in detalhe["versoes"]] == [1, 2]
        assert detalhe["ultima_revisao"]["comentario"] == "Aumentar o contraste."

        geracao = cliente.post(
            f"/api/v1/projetos/{projeto.json()['id']}/templates",
            headers=criador,
            json={"canais": ["instagram_stories"]},
        )
        assert geracao.status_code == 201
        template = geracao.json()["artes"][0]
        assert template["dimensoes"] == "1080 × 1920"
        arquivo = cliente.get(template["imagem_url"], headers=criador)
        assert arquivo.status_code == 200
        with Image.open(io.BytesIO(arquivo.content)) as renderizada:
            assert renderizada.size == (1080, 1920)

        novos_campos = {"produto": "Shampoo 400 ml", "preco": "19,90",
                        "objetivo": "Nova chamada", "informacoes_obrigatorias": "Material demonstrativo"}
        previa = cliente.post(
            f"/api/v1/artes/{template['id']}/template/preview",
            headers=criador,
            json=novos_campos,
        )
        assert previa.status_code == 200
        assert previa.content != arquivo.content
        salva = cliente.post(
            f"/api/v1/artes/{template['id']}/template/versoes",
            headers=criador,
            json=novos_campos,
        )
        assert salva.status_code == 201
        assert salva.json()["versao_atual"] == 2
        assert cliente.get(
            f"/api/v1/artes/{template['id']}/versoes/1/imagem", headers=criador
        ).content == arquivo.content
        monkeypatch.setattr(settings, "max_arte_mb", 0)
        grande = cliente.post(
            f"/api/v1/projetos/{projeto.json()['id']}/artes?canal=instagram_feed",
            headers=criador,
            files={"file": ("grande.png", imagem.getvalue(), "image/png")},
        )
        assert grande.status_code == 413
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)

