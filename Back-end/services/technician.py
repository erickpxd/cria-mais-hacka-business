"""Checagens baratas (milissegundos) feitas ANTES de chamar o modelo de visão."""
import cv2
import numpy as np

from app.config import settings


def decodificar(contents: bytes) -> np.ndarray | None:
    """Bytes do upload -> matriz BGR. Devolve None se não for uma imagem válida."""
    return cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)


def checar_tecnico(img: np.ndarray) -> list[str]:
    problemas: list[str] = []
    h, w = img.shape[:2]

    if w < settings.min_largura or h < settings.min_altura:
        problemas.append(
            f"Resolução {w}x{h} abaixo do mínimo "
            f"{settings.min_largura}x{settings.min_altura}."
        )

    esperado = settings.proporcao_largura / settings.proporcao_altura
    atual = w / h
    if abs(atual - esperado) > settings.tolerancia_proporcao:
        problemas.append(
            f"Proporção {atual:.2f} fora do esperado "
            f"({settings.proporcao_largura}:{settings.proporcao_altura})."
        )

    nitidez = cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
    if nitidez < settings.min_nitidez:
        problemas.append(f"Imagem borrada (nitidez {nitidez:.0f}).")

    return problemas