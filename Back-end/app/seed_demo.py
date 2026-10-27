"""Cria uma base demonstrativa pequena, coerente e livre de dados de testes E2E."""

from datetime import datetime, timezone

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Aprovacao, Arte, EventoDecisao, Projeto, VersaoArte
from app.services import armazenamento, templates
from app.services.formatos import FORMATOS

DEMO_PROJECTS = (
    {
        "nome": "Festival de Ofertas Pague Menos",
        "objetivo": "Destacar uma oferta de cuidado diário com comunicação simples e acessível.",
        "descricao": "Campanha promocional multicanal para as lojas Pague Menos.",
        "produto": "Shampoo 400 ml",
        "preco_centavos": 1790,
        "informacoes_obrigatorias": "Oferta válida enquanto durarem os estoques.",
        "canais": ("instagram_feed", "instagram_stories"),
        "status": "em_producao",
        "arte_dados": {
            "preco_centavos": 1990,
            "objetivo": "Promoçao especial de cuidado diario.",
        },
    },
    {
        "nome": "Semana da Saúde",
        "objetivo": "Incentivar hábitos de cuidado e prevenção com uma oferta relevante.",
        "descricao": "Comunicação de saúde e bem-estar para redes sociais.",
        "produto": "Vitamina C 30 comprimidos",
        "preco_centavos": 2490,
        "informacoes_obrigatorias": "Consulte condições e disponibilidade nas lojas.",
        "canais": ("instagram_feed",),
        "status": "aprovada",
    },
    {
        "nome": "Verão com Proteção",
        "objetivo": "Reforçar o cuidado diário com a pele durante o verão.",
        "descricao": "Campanha sazonal com peças para feed e stories.",
        "produto": "Protetor Solar FPS 50",
        "preco_centavos": 4990,
        "informacoes_obrigatorias": "Use o produto conforme as orientações da embalagem.",
        "canais": ("instagram_feed", "instagram_stories"),
        "status": "em_producao",
        "arte_dados_por_canal": {
            "instagram_stories": {"informacoes_obrigatorias": ""},
        },
    },
)


def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Projeto)):
            return

        for item in DEMO_PROJECTS:
            projeto = Projeto(
                nome=item["nome"], objetivo=item["objetivo"], descricao=item["descricao"],
                produto=item["produto"], preco_centavos=item["preco_centavos"],
                informacoes_obrigatorias=item["informacoes_obrigatorias"],
                orientacoes="Aplicar a identidade visual Pague Menos em vermelho, branco e azul.",
                canais=list(item["canais"]), criado_por="ana",
            )
            db.add(projeto)
            db.flush()

            for canal in item["canais"]:
                formato = FORMATOS[canal]
                dados_arte = {
                    **templates.dados_do_projeto(projeto),
                    **item.get("arte_dados", {}),
                    **item.get("arte_dados_por_canal", {}).get(canal, {}),
                }
                arte = Arte(
                    projeto_id=projeto.id,
                    nome=f"{item['nome']} — {formato['nome']}",
                    canal=canal, status=item["status"], criado_por="ana",
                    enviada_em=(datetime.now(timezone.utc).replace(tzinfo=None)
                                if item["status"] in {"aguardando_aprovacao", "aprovada"} else None),
                )
                db.add(arte)
                db.flush()
                conteudo = templates.renderizar(projeto, canal, dados_arte)
                arquivo = armazenamento.salvar(f"artes/{arte.id}", "v1.png", conteudo)
                db.add(VersaoArte(
                    arte_id=arte.id, numero=1, arquivo=arquivo,
                    largura=formato["largura"], altura=formato["altura"], origem="demo",
                    nota="Arte demonstrativa para validação das regras Pague Menos.",
                    template_dados=None, criado_por="ana",
                ))
                if item["status"] == "aprovada":
                    db.add(Aprovacao(
                        arte_id=arte.id, versao_numero=1, decisao="aprovada",
                        revisor="rafael", comentario="Peça aprovada para a demonstração.",
                    ))

            db.add(EventoDecisao(
                tipo="projeto_demo_criado", usuario="ana",
                payload={"projeto_id": projeto.id, "nome": projeto.nome},
            ))

        db.commit()


if __name__ == "__main__":
    seed()
