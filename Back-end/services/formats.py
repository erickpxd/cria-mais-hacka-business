"""Formatos de publicação. Feed e Stories vêm do design (1080x1080 e 1080x1920).
WhatsApp ('Modelo configurável') e Banner ('Conforme o briefing') NÃO têm medida no design:
os valores abaixo são PROVISÓRIOS, confirme com a equipe."""
import re

FORMATOS = {
    "instagram_feed": {"nome": "Instagram Feed", "largura": 1080, "altura": 1080,
                       "descricao": "Peça quadrada", "provisorio": False},
    "instagram_stories": {"nome": "Instagram Stories", "largura": 1080, "altura": 1920,
                          "descricao": "Peça vertical", "provisorio": False},
    "whatsapp": {"nome": "WhatsApp", "largura": 1080, "altura": 1080,
                 "descricao": "Modelo configurável", "provisorio": True},
    "banner_site": {"nome": "Banner do site", "largura": 1920, "altura": 600,
                    "descricao": "Conforme o briefing", "provisorio": True},
}


def nome_canal(slug: str) -> str:
    return FORMATOS.get(slug, {}).get("nome", slug)


def detectar_canais(texto: str) -> list[str]:
    t = texto.lower()
    achados = []
    if re.search(r"feed", t):
        achados.append("instagram_feed")
    if re.search(r"stor(y|ies)", t):
        achados.append("instagram_stories")
    if re.search(r"whats", t):
        achados.append("whatsapp")
    if re.search(r"banner", t):
        achados.append("banner_site")
    return achados