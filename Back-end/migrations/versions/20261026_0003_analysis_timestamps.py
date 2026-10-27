"""Rastreia início, fim e versão do motor de análise.

Revision ID: 20261026_0003
Revises: 20261025_0002
"""
import sqlalchemy as sa
from alembic import op

revision = "20261026_0003"
down_revision = "20261025_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    colunas = {coluna["name"] for coluna in sa.inspect(op.get_bind()).get_columns("analises")}
    if "engine_version" not in colunas:
        op.add_column("analises", sa.Column("engine_version", sa.String(length=80),
                                            nullable=False, server_default="paddleocr-local"))
    if "iniciada_em" not in colunas:
        op.add_column("analises", sa.Column("iniciada_em", sa.DateTime(), nullable=True))
    if "finalizada_em" not in colunas:
        op.add_column("analises", sa.Column("finalizada_em", sa.DateTime(), nullable=True))


def downgrade() -> None:
    colunas = {coluna["name"] for coluna in sa.inspect(op.get_bind()).get_columns("analises")}
    for nome in ("finalizada_em", "iniciada_em", "engine_version"):
        if nome in colunas:
            op.drop_column("analises", nome)
