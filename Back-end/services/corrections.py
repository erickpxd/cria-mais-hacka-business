"""Aplica as correções ACEITAS numa cópia da arte (a v1 nunca é tocada).

Método (simples, bom para fundos lisos como nas artes de campanha):
  apaga o texto antigo pintando com a cor do fundo ao redor e desenha o texto corrigido
  com a cor do texto original. Em fundos com foto/degradê forte o resultado pode ficar
  visível: por isso toda versão corrigida passa por revisão humana."""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTES = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"]


def _fonte(tamanho: int):
    for f in FONTES:
        try:
            return ImageFont.truetype(f, tamanho)
        except OSError:
            continue
    return ImageFont.load_default(tamanho)


def _cor_fundo(arr: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
    H, W = arr.shape[:2]
    pad = 6
    x0, y0, x1, y1 = max(x - pad, 0), max(y - pad, 0), min(x + w + pad, W), min(y + h + pad, H)
    bloco = arr[y0:y1, x0:x1]
    mascara = np.ones(bloco.shape[:2], bool)
    mascara[(y - y0):(y - y0 + h), (x - x0):(x - x0 + w)] = False  # tira o miolo (o texto)
    return np.median(bloco[mascara], axis=0).astype(int)


def aplicar_correcoes(img_bgr: np.ndarray, itens: list[tuple[dict, str]]) -> np.ndarray:
    """itens = [(regiao{x,y,w,h}, linha_corrigida)]"""
    pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    arr = np.asarray(pil).copy()
    draw = ImageDraw.Draw(pil)
    for regiao, texto in itens:
        x, y, w, h = (int(regiao[k]) for k in ("x", "y", "w", "h"))
        fundo = _cor_fundo(arr, x, y, w, h)
        miolo = arr[y:y + h, x:x + w].reshape(-1, 3).astype(int)
        dist = np.linalg.norm(miolo - fundo, axis=1)
        frente = miolo[dist >= 0.7 * dist.max()].mean(axis=0) if dist.max() > 0 else fundo
        draw.rectangle([x - 2, y - 2, x + w + 2, y + h + 2], fill=tuple(int(v) for v in fundo))
        tamanho = max(int(h * 1.05), 8)
        fonte = _fonte(tamanho)
        while tamanho > 8 and draw.textlength(texto, font=fonte) > w * 1.12:
            tamanho -= 1
            fonte = _fonte(tamanho)
        draw.text((x, y + h / 2), texto, font=fonte, fill=tuple(int(v) for v in frente), anchor="lm")
    return cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)