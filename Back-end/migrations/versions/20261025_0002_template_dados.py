"""Campos editáveis usados para reproduzir versões de template.

Revision ID: 20261025_0002
Revises: 20261025_0001
"""
import sqlalchemy as sa
from alembic import op

revision = "20261025_0002"
down_revision = "20261025_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    colunas = {coluna["name"] for coluna in sa.inspect(op.get_bind()).get_columns("versoes_arte")}
    if "template_dados" not in colunas:
        op.add_column("versoes_arte", sa.Column("template_dados", sa.JSON(), nullable=True))


def downgrade() -> None:
    colunas = {coluna["name"] for coluna in sa.inspect(op.get_bind()).get_columns("versoes_arte")}
    if "template_dados" in colunas:
        op.drop_column("versoes_arte", "template_dados")
