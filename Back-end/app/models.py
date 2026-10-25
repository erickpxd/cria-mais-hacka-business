from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # UTC "ingênuo"


class Projeto(Base):
    __tablename__ = "projetos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    objetivo: Mapped[str | None] = mapped_column(Text, default=None)
    descricao: Mapped[str | None] = mapped_column(Text, default=None)
    prazo: Mapped[date | None] = mapped_column(Date, default=None)
    produto: Mapped[str | None] = mapped_column(String(300), default=None)
    preco_centavos: Mapped[int | None] = mapped_column(default=None)
    informacoes_obrigatorias: Mapped[str | None] = mapped_column(Text, default=None)
    orientacoes: Mapped[str | None] = mapped_column(Text, default=None)
    canais: Mapped[list] = mapped_column(JSON, default=list)
    briefing_arquivo: Mapped[str | None] = mapped_column(String(300), default=None)
    briefing_nome: Mapped[str | None] = mapped_column(String(300), default=None)
    briefing_campos: Mapped[dict | None] = mapped_column(JSON, default=None)  # com a página de cada campo
    criado_por: Mapped[str] = mapped_column(String(50))
    criado_em: Mapped[datetime] = mapped_column(default=agora)
    atualizado_em: Mapped[datetime] = mapped_column(default=agora, onupdate=agora)

    artes: Mapped[list["Arte"]] = relationship(
        back_populates="projeto", cascade="all, delete-orphan", order_by="Arte.id"
    )


class Arte(Base):
    __tablename__ = "artes"

    id: Mapped[int] = mapped_column(primary_key=True)
    projeto_id: Mapped[int] = mapped_column(ForeignKey("projetos.id"))
    nome: Mapped[str] = mapped_column(String(200))
    canal: Mapped[str] = mapped_column(String(50))
    # em_analise | em_producao | precisa_ajustes | aguardando_aprovacao | aprovada
    status: Mapped[str] = mapped_column(String(30), default="em_analise")
    # pronta | gerando | erro   (usado nas artes criadas por adaptação)
    geracao: Mapped[str] = mapped_column(String(20), default="pronta")
    geracao_erro: Mapped[str | None] = mapped_column(Text, default=None)
    arte_origem_id: Mapped[int | None] = mapped_column(ForeignKey("artes.id"), default=None)
    criado_por: Mapped[str] = mapped_column(String(50))
    criado_em: Mapped[datetime] = mapped_column(default=agora)
    enviada_em: Mapped[datetime | None] = mapped_column(default=None)

    projeto: Mapped[Projeto] = relationship(back_populates="artes")
    versoes: Mapped[list["VersaoArte"]] = relationship(
        back_populates="arte", cascade="all, delete-orphan", order_by="VersaoArte.numero"
    )
    comentarios: Mapped[list["Comentario"]] = relationship(
        cascade="all, delete-orphan", order_by="Comentario.id"
    )


class VersaoArte(Base):
    """v1 é SEMPRE a original e nunca é alterada: correções e adaptações geram novas versões."""

    __tablename__ = "versoes_arte"

    id: Mapped[int] = mapped_column(primary_key=True)
    arte_id: Mapped[int] = mapped_column(ForeignKey("artes.id"))
    numero: Mapped[int]
    arquivo: Mapped[str] = mapped_column(String(300))
    largura: Mapped[int]
    altura: Mapped[int]
    origem: Mapped[str] = mapped_column(String(20))  # upload | correcao | adaptacao
    nota: Mapped[str | None] = mapped_column(Text, default=None)
    criado_por: Mapped[str] = mapped_column(String(50))
    criado_em: Mapped[datetime] = mapped_column(default=agora)

    arte: Mapped[Arte] = relationship(back_populates="versoes")
    analise: Mapped["Analise | None"] = relationship(
        back_populates="versao", cascade="all, delete-orphan", uselist=False
    )


class Analise(Base):
    __tablename__ = "analises"

    id: Mapped[int] = mapped_column(primary_key=True)
    versao_id: Mapped[int] = mapped_column(ForeignKey("versoes_arte.id"), unique=True)
    estado: Mapped[str] = mapped_column(String(20), default="concluida")  # concluida | erro
    erro: Mapped[str | None] = mapped_column(Text, default=None)
    verificacoes_aplicadas: Mapped[list] = mapped_column(JSON, default=list)
    notas: Mapped[list] = mapped_column(JSON, default=list)
    linhas_ocr: Mapped[list] = mapped_column(JSON, default=list)
    executada_em: Mapped[datetime] = mapped_column(default=agora)

    versao: Mapped[VersaoArte] = relationship(back_populates="analise")
    achados: Mapped[list["Achado"]] = relationship(
        cascade="all, delete-orphan", order_by="Achado.ordem"
    )


class Achado(Base):
    __tablename__ = "achados"

    id: Mapped[int] = mapped_column(primary_key=True)
    analise_id: Mapped[int] = mapped_column(ForeignKey("analises.id"))
    ordem: Mapped[int]
    tipo: Mapped[str] = mapped_column(String(40))  # preco_divergente | erro_escrita | texto_na_borda
    titulo: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str] = mapped_column(Text)
    regiao: Mapped[dict | None] = mapped_column(JSON, default=None)
    sugestao: Mapped[dict | None] = mapped_column(JSON, default=None)
    referencia: Mapped[str | None] = mapped_column(String(200), default=None)
    decisao: Mapped[str] = mapped_column(String(20), default="pendente")  # pendente|aceito|rejeitado
    decidido_por: Mapped[str | None] = mapped_column(String(50), default=None)
    decidido_em: Mapped[datetime | None] = mapped_column(default=None)


class Comentario(Base):
    __tablename__ = "comentarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    arte_id: Mapped[int] = mapped_column(ForeignKey("artes.id"))
    versao_numero: Mapped[int]
    autor: Mapped[str] = mapped_column(String(50))
    texto: Mapped[str] = mapped_column(Text)
    regiao: Mapped[dict | None] = mapped_column(JSON, default=None)
    criado_em: Mapped[datetime] = mapped_column(default=agora)


class Aprovacao(Base):
    __tablename__ = "aprovacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    arte_id: Mapped[int] = mapped_column(ForeignKey("artes.id"))
    versao_numero: Mapped[int]
    decisao: Mapped[str] = mapped_column(String(20))  # aprovada | devolvida
    revisor: Mapped[str] = mapped_column(String(50))
    comentario: Mapped[str | None] = mapped_column(Text, default=None)
    em: Mapped[datetime] = mapped_column(default=agora)


class EventoDecisao(Base):
    """Registro de TODA decisão humana desde o dia 1 (base para o ML clássico futuro)."""

    __tablename__ = "eventos_decisao"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(50))
    usuario: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    em: Mapped[datetime] = mapped_column(default=agora)