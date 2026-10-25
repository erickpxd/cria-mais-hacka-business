"""Leitura de texto da arte (PaddleOCR). Fica atrás de uma interface para trocar de motor sem mexer nas regras."""
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from app.config import settings
from app.services.erros import ErroServicoIA


@dataclass
class LinhaTexto:
    texto: str
    x: int
    y: int
    w: int
    h: int
    confianca: float


class MotorOCR(Protocol):
    def ler(self, img_bgr: np.ndarray) -> list[LinhaTexto]: ...


class MotorPaddle:
    """PaddleOCR 3.x: PaddleOCR(...).predict(imagem) -> [{rec_texts, rec_scores, rec_polys, ...}]"""

    def __init__(self) -> None:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise ErroServicoIA(503, "PaddleOCR não está instalado no back-end.") from exc
        self._ocr = PaddleOCR(
            lang=settings.ocr_lang,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )

    def ler(self, img_bgr: np.ndarray) -> list[LinhaTexto]:
        resultado = self._ocr.predict(img_bgr)
        linhas: list[LinhaTexto] = []
        for pagina in resultado:
            textos = pagina["rec_texts"]
            notas = pagina["rec_scores"]
            polys = pagina["rec_polys"]
            for texto, nota, poly in zip(textos, notas, polys):
                pts = np.asarray(poly)
                x0, y0 = pts[:, 0].min(), pts[:, 1].min()
                x1, y1 = pts[:, 0].max(), pts[:, 1].max()
                linhas.append(LinhaTexto(str(texto), int(x0), int(y0), int(x1 - x0), int(y1 - y0), float(nota)))
        return linhas


_motor: MotorOCR | None = None


def obter_motor() -> MotorOCR:
    global _motor
    if _motor is None:
        if settings.ocr_motor == "paddle":
            _motor = MotorPaddle()
        else:
            raise ErroServicoIA(500, f"Motor de OCR desconhecido: {settings.ocr_motor}")
    return _motor


def definir_motor(motor: MotorOCR | None) -> None:
    """Usado nos testes para injetar um motor falso."""
    global _motor
    _motor = motor