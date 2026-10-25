"""Ortografia via LanguageTool LOCAL (container). Só aponta erros de escrita (TYPOS/misspelling)."""
from dataclasses import dataclass

import httpx

from app.config import settings
from app.services.erros import ErroServicoIA


@dataclass
class ErroEscrita:
    linha: int          # índice da linha enviada
    inicio: int         # posição dentro da linha
    tamanho: int
    palavra: str
    sugestoes: list[str]


async def verificar_linhas(linhas: list[str]) -> list[ErroEscrita]:
    if not linhas:
        return []
    texto = "\n".join(linhas)
    inicios, pos = [], 0
    for l in linhas:
        inicios.append(pos)
        pos += len(l) + 1

    try:
        async with httpx.AsyncClient(timeout=settings.languagetool_timeout) as http:
            r = await http.post(
                f"{settings.languagetool_url.rstrip('/')}/v2/check",
                data={"language": settings.languagetool_lang, "text": texto},
            )
            r.raise_for_status()
    except httpx.TimeoutException as exc:
        raise ErroServicoIA(504, "O LanguageTool demorou demais para responder.") from exc
    except (httpx.TransportError, httpx.HTTPStatusError) as exc:
        raise ErroServicoIA(503, "O LanguageTool está indisponível.") from exc

    erros: list[ErroEscrita] = []
    for m in r.json().get("matches", []):
        regra = m.get("rule", {})
        if regra.get("issueType") != "misspelling" and regra.get("category", {}).get("id") != "TYPOS":
            continue
        off, tam = m["offset"], m["length"]
        idx = max(i for i, ini in enumerate(inicios) if ini <= off)
        erros.append(ErroEscrita(
            linha=idx, inicio=off - inicios[idx], tamanho=tam,
            palavra=texto[off:off + tam],
            sugestoes=[x["value"] for x in m.get("replacements", [])][:3],
        ))
    return erros