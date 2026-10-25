from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import exigir_revisor, usuario_atual
from app.models import Aprovacao, Arte, EventoDecisao, agora
from app.serializers import (iso, nome_usuario, ser_analise, ser_arte, ser_comentario, ser_versao, versao_atual)
from app.services import storage as armazenamento
from app.services.erros import ErroNegocio
from app.services.formatos import nome_canal

router = APIRouter(prefix="/api")

AVISO_APROVACAO = "A aprovação foi feita por uma pessoa. Não representa garantia de conformidade legal ou regulatória."
AVISO_AUTOMATICO = "A legibilidade e o contexto dependem da sua avaliação."


def _ultima_decisao(db: Session, arte_id: int) -> Aprovacao | None:
    return db.scalars(select(Aprovacao).where(Aprovacao.arte_id == arte_id).order_by(Aprovacao.id.desc())).first()


def _arte(db: Session, arte_id: int) -> Arte:
    a = db.get(Arte, arte_id)
    if not a:
        raise HTTPException(404, "Arte não encontrada.")
    return a


@router.get("/aprovacoes")
def listar(aba: str = "pendentes", campanha: int | None = None, canal: str | None = None,
           db: Session = Depends(get_db), usuario: dict = Depends(usuario_atual)):
    """Abas do design: Pendentes | Aprovadas | Devolvidas."""
    if aba not in ("pendentes", "aprovadas", "devolvidas"):
        raise ErroNegocio(422, "Aba inválida. Use pendentes, aprovadas ou devolvidas.")
    artes = db.scalars(select(Arte).order_by(Arte.enviada_em.desc(), Arte.id.desc())).all()
    itens = []
    for a in artes:
        ult = _ultima_decisao(db, a.id)
        if aba == "pendentes" and a.status != "aguardando_aprovacao":
            continue
        if aba == "aprovadas" and a.status != "aprovada":
            continue
        if aba == "devolvidas" and not (a.status == "precisa_ajustes" and ult and ult.decisao == "devolvida"):
            continue
        if campanha and a.projeto_id != campanha:
            continue
        if canal and a.canal != canal:
            continue
        d = ser_arte(a)
        d.update({"projeto_nome": a.projeto.nome, "decidido_por": nome_usuario(ult.revisor) if ult else None,
                  "decidido_em": iso(ult.em) if ult else None})
        itens.append(d)
    contagem = {k: 0 for k in ("pendentes", "aprovadas", "devolvidas")}
    for a in artes:
        ult = _ultima_decisao(db, a.id)
        if a.status == "aguardando_aprovacao":
            contagem["pendentes"] += 1
        elif a.status == "aprovada":
            contagem["aprovadas"] += 1
        elif a.status == "precisa_ajustes" and ult and ult.decisao == "devolvida":
            contagem["devolvidas"] += 1
    return {"aba": aba, "contagem": contagem, "total_exibido": len(itens), "itens": itens,
            "aviso": "Confira a arte, o briefing e o histórico. As verificações automáticas apoiam a revisão, mas a decisão é da equipe."}


@router.get("/aprovacoes/{arte_id}")
def avaliar(arte_id: int, db: Session = Depends(get_db), usuario: dict = Depends(usuario_atual)):
    """Tudo que a tela 'Avaliar arte' precisa."""
    a = _arte(db, arte_id)
    v = versao_atual(a)
    ult = _ultima_decisao(db, a.id)
    d = ser_arte(a)
    an = ser_analise(v.analise) if v else None
    d.update({
        "projeto_nome": a.projeto.nome, "canal_nome": nome_canal(a.canal),
        "breadcrumb": f"{a.nome} / {a.projeto.nome} / {nome_canal(a.canal)}",
        "verificacoes": {"concluidas": bool(an and an["estado"] == "concluida"),
                         "aplicadas": an["verificacoes_aplicadas"] if an else [],
                         "notas": an["notas"] if an else [], "aviso": AVISO_AUTOMATICO,
                         "achados_pendentes": an["total_pendentes"] if an else 0},
        "comentarios": [ser_comentario(c, i + 1) for i, c in enumerate(a.comentarios)],
        "versoes": [ser_versao(x, x is v) for x in reversed(a.versoes)],
        "decisao": ({"decisao": ult.decisao, "revisor": nome_usuario(ult.revisor), "em": iso(ult.em),
                     "versao": ult.versao_numero, "comentario": ult.comentario,
                     "aviso": AVISO_APROVACAO if ult.decisao == "aprovada" else None} if ult else None),
        "pode_decidir": usuario["papel"] == "revisor" and a.status == "aguardando_aprovacao",
        "exportacao_liberada": a.status == "aprovada",
        "tem_briefing": bool(a.projeto.briefing_arquivo),
        "briefing_url": f"/api/projetos/{a.projeto_id}/briefing" if a.projeto.briefing_arquivo else None,
    })
    return d


class AjustesIn(BaseModel):
    comentario: str


def _precisa_aguardando(a: Arte) -> None:
    if a.status != "aguardando_aprovacao":
        raise ErroNegocio(409, "Esta arte não está aguardando aprovação.")


@router.post("/artes/{arte_id}/aprovar")
def aprovar(arte_id: int, db: Session = Depends(get_db), usuario: dict = Depends(usuario_atual)):
    exigir_revisor(usuario)
    a = _arte(db, arte_id)
    _precisa_aguardando(a)
    if a.criado_por == usuario["id"]:
        raise ErroNegocio(403, "Você não pode aprovar a própria arte.")
    v = versao_atual(a)
    db.add(Aprovacao(arte_id=a.id, versao_numero=v.numero, decisao="aprovada", revisor=usuario["id"]))
    db.add(EventoDecisao(tipo="arte_aprovada", usuario=usuario["id"], payload={"arte_id": a.id, "versao": v.numero}))
    a.status = "aprovada"
    db.commit()
    return {"mensagem": "Aprovação registrada.", "aviso": AVISO_APROVACAO,
            "aprovada_por": usuario["nome"], "versao": v.numero, "em": iso(agora()),
            "exportar_url": f"/api/artes/{a.id}/exportar"}


@router.post("/artes/{arte_id}/solicitar-ajustes")
def solicitar_ajustes(arte_id: int, corpo: AjustesIn, db: Session = Depends(get_db),
                      usuario: dict = Depends(usuario_atual)):
    exigir_revisor(usuario)
    a = _arte(db, arte_id)
    _precisa_aguardando(a)
    if not corpo.comentario.strip():
        raise ErroNegocio(422, "Explique o que precisa mudar.")
    v = versao_atual(a)
    db.add(Aprovacao(arte_id=a.id, versao_numero=v.numero, decisao="devolvida", revisor=usuario["id"],
                     comentario=corpo.comentario.strip()))
    db.add(EventoDecisao(tipo="arte_devolvida", usuario=usuario["id"],
                         payload={"arte_id": a.id, "versao": v.numero, "regioes": len(a.comentarios)}))
    a.status = "precisa_ajustes"
    db.commit()
    return {"mensagem": f"Arte devolvida para {nome_usuario(a.criado_por)}.", "regioes": len(a.comentarios)}


@router.get("/artes/{arte_id}/exportar")
def exportar(arte_id: int, db: Session = Depends(get_db), usuario: dict = Depends(usuario_atual)):
    """Só exporta depois da aprovação HUMANA, e exporta exatamente a versão aprovada."""
    a = _arte(db, arte_id)
    ult = _ultima_decisao(db, a.id)
    if a.status != "aprovada" or not ult or ult.decisao != "aprovada":
        raise HTTPException(403, "Exportação disponível após a aprovação humana.")
    v = next(x for x in a.versoes if x.numero == ult.versao_numero)
    db.add(EventoDecisao(tipo="arte_exportada", usuario=usuario["id"], payload={"arte_id": a.id, "versao": v.numero}))
    db.commit()
    ext = v.arquivo.rsplit(".", 1)[-1]
    return FileResponse(armazenamento.caminho(v.arquivo), filename=f"{a.nome.replace(' ', '_')}_v{v.numero}.{ext}")