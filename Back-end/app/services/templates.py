"""Renderização determinística de peças da POC a partir de um template controlado."""
import io
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont

from app.services.briefing import formatar_preco
from app.services.formatos import FORMATOS

FONTES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)

# Paleta institucional usada nas peças da POC para o cliente Pague Menos.
AZUL = "#1238A6"
VERMELHO = "#ED1C2E"
BRANCO = "#FFFFFF"
FUNDO = "#F3F6FF"
TEXTO_SUAVE = "#DCE5FF"


def _fonte(tamanho: int, regular: bool = False):
    caminho = FONTES[1 if regular else 0]
    try:
        return ImageFont.truetype(caminho, tamanho)
    except OSError:
        return ImageFont.load_default()


def _linhas(texto: str, limite: int) -> list[str]:
    return wrap(texto.strip(), width=max(limite, 12), break_long_words=False) or [""]


def dados_do_projeto(projeto) -> dict:
    return {"produto": projeto.produto or projeto.nome,
            "preco_centavos": projeto.preco_centavos,
            "objetivo": projeto.objetivo or "",
            "informacoes_obrigatorias": projeto.informacoes_obrigatorias or ""}


def renderizar(projeto, canal: str, dados: dict | None = None) -> bytes:
    """Gera um PNG real; os campos vêm exclusivamente do briefing persistido."""
    formato = FORMATOS[canal]
    largura, altura = formato["largura"], formato["altura"]
    imagem = Image.new("RGB", (largura, altura), FUNDO)
    desenho = ImageDraw.Draw(imagem)

    # Composição responsiva com a mesma hierarquia para todos os canais.
    vertical = altura > largura * 1.25
    margem = int(min(largura, altura) * 0.07)
    raio = max(24, margem // 2)
    desenho.rounded_rectangle(
        (margem, margem, largura - margem, altura - margem),
        radius=raio,
        fill=AZUL,
    )
    # Elementos vermelhos reforçam a marca sem competir com a oferta.
    desenho.ellipse(
        (largura * 0.73, -altura * 0.06, largura * 1.10, altura * 0.25),
        fill=VERMELHO,
    )
    desenho.ellipse(
        (-largura * 0.20, altura * 0.66, largura * 0.16, altura * 0.88),
        fill=VERMELHO,
    )

    x = margem * 2
    y = margem * (3 if vertical else 2)
    unidade = max(8, int(min(largura, altura) * 0.012))

    # Assinatura Pague Menos construída em formas vetoriais simples.
    simbolo = unidade * 5
    desenho.rounded_rectangle((x, y, x + simbolo, y + simbolo), radius=unidade, fill=VERMELHO)
    haste = max(4, unidade)
    centro_x, centro_y = x + simbolo // 2, y + simbolo // 2
    desenho.rounded_rectangle(
        (centro_x - haste // 2, y + unidade, centro_x + haste // 2, y + simbolo - unidade),
        radius=haste // 2, fill=BRANCO,
    )
    desenho.rounded_rectangle(
        (x + unidade, centro_y - haste // 2, x + simbolo - unidade, centro_y + haste // 2),
        radius=haste // 2, fill=BRANCO,
    )
    fonte_marca = _fonte(max(22, int(min(largura, altura) * 0.035)))
    desenho.text((x + simbolo + unidade * 1.3, centro_y), "Pague Menos", font=fonte_marca,
                 fill=BRANCO, anchor="lm")

    y += simbolo + margem * (1.25 if vertical else 0.72)
    dados = {**dados_do_projeto(projeto), **(dados or {})}
    titulo = dados["produto"]
    fonte_titulo = _fonte(int(min(largura, altura) * (0.072 if vertical else 0.061)))
    for linha in _linhas(titulo, 16 if vertical else 19):
        desenho.text((x, y), linha, font=fonte_titulo, fill=BRANCO)
        y += int(fonte_titulo.size * 1.15)

    if dados["preco_centavos"] is not None:
        preco = f"R$ {formatar_preco(dados['preco_centavos'])}"
        fonte_preco = _fonte(int(min(largura, altura) * 0.078))
        y += margem // 2
        caixa = desenho.textbbox((0, 0), preco, font=fonte_preco)
        caixa_largura = caixa[2] - caixa[0] + unidade * 4
        caixa_altura = caixa[3] - caixa[1] + unidade * 3
        desenho.rounded_rectangle((x, y, x + caixa_largura, y + caixa_altura),
                                  radius=int(unidade * 1.4), fill=BRANCO)
        desenho.text((x + unidade * 2, y + caixa_altura / 2), preco, font=fonte_preco,
                     fill=VERMELHO, anchor="lm")
        y += caixa_altura + margem // 2

    objetivo = dados["objetivo"]
    fonte_texto = _fonte(int(min(largura, altura) * 0.028), regular=True)
    for linha in _linhas(objetivo, 34 if vertical else 52)[:3]:
        desenho.text((x, y), linha, font=fonte_texto, fill=TEXTO_SUAVE)
        y += int(fonte_texto.size * 1.35)

    obrigatorio = dados["informacoes_obrigatorias"]
    if obrigatorio:
        fonte_legal = _fonte(max(18, int(min(largura, altura) * 0.018)), regular=True)
        legais = _linhas(obrigatorio, 55 if vertical else 80)[:3]
        altura_bloco = len(legais) * int(fonte_legal.size * 1.35)
        legal_y = altura - margem * 2 - altura_bloco
        for linha in legais:
            desenho.text((x, legal_y), linha, font=fonte_legal, fill=BRANCO)
            legal_y += int(fonte_legal.size * 1.35)

    saida = io.BytesIO()
    imagem.save(saida, format="PNG", optimize=True)
    return saida.getvalue()
