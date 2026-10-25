"""Converte os objetos do banco no JSON que o front consome."""
from app.config import settings
from app.models import Achado, Analise, Arte, Comentario, Projeto
from app.services.briefing import formatar_preco
from app.services.formatos import FORMATOS, nome_canal

STATUS_ROTULO = {
    "em_analise": "Em análise",
    "em_producao": "Em produção",
    "precisa_ajustes": "Precisa de ajustes",
    "aguardando_aprovacao": "Aguardando aprovação",
    "aprovada": "Aprovada",
}
ORIGEM_ROTULO = {"upload": "Enviada", "correcao": "Correções aplicadas", "adaptacao": "Adaptada"}


def iso(dt):
    return dt.isoformat() + "Z" if dt else None


def nome_usuario(uid: str) -> str:
    return settings.usuarios.get(uid, {}).get("nome", uid)


def versao_atual(arte: Arte):
    return arte.versoes[-1] if arte.versoes else None


def ser_arte(arte: Arte) -> dict:
    v = versao_atual(arte)
    return {
        "id": arte.id, "projeto_id": arte.projeto_id, "nome": arte.nome,
        "canal": arte.canal, "canal_nome": nome_canal(arte.canal),
        "status": arte.status, "status_rotulo": STATUS_ROTULO.get(arte.status, arte.status),
        "geracao": arte.geracao, "geracao_erro": arte.geracao_erro,
        "arte_origem_id": arte.arte_origem_id,
        "criado_por": nome_usuario(arte.criado_por), "criado_em": iso(arte.criado_em),
        "enviada_em": iso(arte.enviada_em),
        "versao_atual": v.numero if v else None,
        "dimensoes": f"{v.largura} × {v.altura}" if v else None,
        "imagem_url": f"/api/artes/{arte.id}/versoes/{v.numero}/imagem" if v else None,
    }


def ser_versao(v, atual: bool) -> dict:
    return {"numero": v.numero, "origem": v.origem, "origem_rotulo": ORIGEM_ROTULO.get(v.origem, v.origem),
            "nota": v.nota, "criado_por": nome_usuario(v.criado_por), "criado_em": iso(v.criado_em),
            "largura": v.largura, "altura": v.altura, "atual": atual, "original": v.numero == 1,
            "imagem_url": f"/api/artes/{v.arte_id}/versoes/{v.numero}/imagem"}


def ser_achado(a: Achado) -> dict:
    return {"id": a.id, "ordem": a.ordem + 1, "tipo": a.tipo, "titulo": a.titulo, "descricao": a.descricao,
            "regiao": a.regiao, "sugestao": a.sugestao, "referencia": a.referencia,
            "corrigivel": bool(a.sugestao and a.sugestao.get("linha_corrigida")),
            "decisao": a.decisao, "decidido_por": nome_usuario(a.decidido_por) if a.decidido_por else None}


def ser_analise(an: Analise | None) -> dict | None:
    if an is None:
        return None
    pendentes = [a for a in an.achados if a.decisao == "pendente"]
    return {
        "estado": an.estado, "erro": an.erro,
        "verificacoes_aplicadas": an.verificacoes_aplicadas, "notas": an.notas,
        "achados": [ser_achado(a) for a in an.achados],
        "total_achados": len(an.achados), "total_pendentes": len(pendentes),
        "sem_inconsistencias": an.estado == "concluida" and not an.achados,
        "aviso": ("Nenhuma inconsistência detectada. Isso não garante que a arte esteja livre de erros: "
                  "revise o conteúdo e a legibilidade antes de enviar." if an.estado == "concluida" and not an.achados
                  else "As sugestões precisam da avaliação de uma pessoa."),
    }


def ser_comentario(c: Comentario, numero: int) -> dict:
    return {"id": c.id, "numero": numero, "autor": nome_usuario(c.autor), "texto": c.texto,
            "regiao": c.regiao, "versao": c.versao_numero, "criado_em": iso(c.criado_em),
            "origem": "revisão humana"}


def resumo_formatos(projeto: Projeto) -> dict:
    com_arte = {a.canal for a in projeto.artes}
    esperados = list(projeto.canais or [])
    return {
        "esperados": [{"canal": c, "nome": nome_canal(c), "entregue": c in com_arte} for c in esperados],
        "entregues": sum(1 for c in esperados if c in com_arte),
        "total": len(esperados),
        "faltantes": [{"canal": c, "nome": nome_canal(c)} for c in esperados if c not in com_arte],
    }


def ser_projeto_resumo(p: Projeto) -> dict:
    f = resumo_formatos(p)
    ajustes = sum(1 for a in p.artes if a.status == "precisa_ajustes")
    aguardando = sum(1 for a in p.artes if a.status == "aguardando_aprovacao")
    if p.artes and all(a.status == "aprovada" for a in p.artes) and not f["faltantes"]:
        status = ("concluido", "Concluído")
    elif aguardando and not ajustes and not any(a.status in ("em_producao", "em_analise") for a in p.artes):
        status = ("aguardando_aprovacao", "Aguardando aprovação")
    else:
        status = ("em_andamento", "Em andamento")
    capa = next((a for a in p.artes if a.versoes), None)
    return {
        "id": p.id, "nome": p.nome, "status": status[0], "status_rotulo": status[1],
        "total_artes": len(p.artes), "artes_com_ajustes": ajustes, "artes_aguardando": aguardando,
        "formatos": f, "prazo": p.prazo.isoformat() if p.prazo else None,
        "criado_por": nome_usuario(p.criado_por), "atualizado_em": iso(p.atualizado_em),
        "capa_url": f"/api/artes/{capa.id}/versoes/1/imagem" if capa else None,
    }


def ser_projeto_detalhe(p: Projeto) -> dict:
    d = ser_projeto_resumo(p)
    d.update({
        "objetivo": p.objetivo, "descricao": p.descricao, "produto": p.produto,
        "preco": formatar_preco(p.preco_centavos) if p.preco_centavos is not None else None,
        "informacoes_obrigatorias": p.informacoes_obrigatorias, "orientacoes": p.orientacoes,
        "canais": [{"canal": c, "nome": nome_canal(c)} for c in p.canais or []],
        "tem_briefing": bool(p.briefing_arquivo), "briefing_nome": p.briefing_nome,
        "briefing_url": f"/api/projetos/{p.id}/briefing" if p.briefing_arquivo else None,
        "artes": [ser_arte(a) for a in p.artes],
        "alertas": [f"Falta uma versão para {x['nome']}." for x in d["formatos"]["faltantes"]],
    })
    return d


def ser_formatos() -> list[dict]:
    return [{"canal": k, **v} for k, v in FORMATOS.items()]