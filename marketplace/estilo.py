"""Identidade visual: o que o tema de .streamlit/config.toml não cobre."""
import base64

import plotly.express as px
import streamlit as st

ROSA = "#FE0B5D"
CORES_GRAFICOS = [ROSA, "#1F5FA8", "#B3013B", "#C77700"]

_SOL = (
    "M96.8 39.2Q90.9 42.2 68.9 53.2Q86.1 70.6 90.7 75.4Q84.4 73.4 61.1 65.6Q60.9 90.1 60.8 96.8"
    "Q57.8 90.9 46.8 68.9Q29.4 86.1 24.6 90.7Q26.6 84.4 34.4 61.1Q9.9 60.9 3.2 60.8Q9.1 57.8 31.1 46.8"
    "Q13.9 29.4 9.3 24.6Q15.6 26.6 38.9 34.4Q39.1 9.9 39.2 3.2Q42.2 9.1 53.2 31.1Q70.6 13.9 75.4 9.3"
    "Q73.4 15.6 65.6 38.9Q90.1 39.1 96.8 39.2Z"
)

_CSS = """
<style>
[data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"] {
    margin: 0;
    padding: 0;
}
[class*="st-key-menu_"] [data-testid="stElementContainer"] {
    margin: 0;
}
[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] {
    gap: 0;
}
[class*="st-key-menu_"] a {
    display: flex;
    align-items: center;
    width: 100%;
    min-height: 48px;
    box-sizing: border-box;
    margin: 0;
    padding: 10px 32px;
    border-radius: 0;
    border-bottom: 1px solid #FE0B5D;
}
[class*="st-key-menu_"] a p {
    color: #000000;
    font-size: 15px;
    letter-spacing: 0.3em;
    text-transform: uppercase;
}
.st-key-menu_marca a,
.st-key-menu_ativo a,
[class*="st-key-menu_"] a:hover {
    background: #FE0B5D;
}
.st-key-menu_marca a {
    border-bottom-color: #000000;
}
.st-key-menu_busca {
    padding: 10px 32px;
    border-bottom: 1px solid #FE0B5D;
}
.st-key-menu_busca label p {
    letter-spacing: 0.3em;
    text-transform: uppercase;
}
.st-key-menu_sol {
    padding: 32px;
}
.st-key-trilha {
    padding-bottom: 12px;
    border-bottom: 1px solid #FE0B5D;
}
.st-key-trilha a {
    padding: 0;
}
.st-key-trilha a p,
.st-key-trilha [data-testid="stText"] {
    color: #000000;
    font-family: "Jost", sans-serif;
    font-size: 13px;
    letter-spacing: 0.24em;
}
/* O rosa não dá contraste com texto branco: botões principais usam texto preto */
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primaryFormSubmit"],
[data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-primaryFormSubmit"] p {
    color: #000000;
}
[class*="st-key-card_"] h3 {
    font-size: 1.4rem;
    font-weight: 400;
    line-height: 1.2;
    padding-top: 0;
}
</style>
"""


def sol_svg(tamanho=144, cor=ROSA):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" aria-hidden="true" width="{tamanho}" height="{tamanho}" viewBox="0 0 100 100" '
        f'fill="{cor}" stroke="{cor}" stroke-width="1.5" stroke-linejoin="round">'
        f'<path d="{_SOL}"></path></svg>'
    )


def sol_html(tamanho=144):
    """Sol como imagem: st.html remove tags <svg> ao sanitizar o conteúdo."""
    dados = base64.b64encode(sol_svg(tamanho).encode()).decode()
    return f'<img alt="" width="{tamanho}" height="{tamanho}" src="data:image/svg+xml;base64,{dados}">'


def aplicar_estilo():
    px.defaults.color_discrete_sequence = CORES_GRAFICOS  # o tema não alcança as pizzas
    st.html(_CSS)
