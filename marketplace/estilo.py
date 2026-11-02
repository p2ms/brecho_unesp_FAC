"""Identidade visual: o que o tema de .streamlit/config.toml não cobre."""
import base64

import plotly.express as px
import streamlit as st

ROSA = "#FE0B5D"
VINHO = "#B3013B"
CORES_GRAFICOS = [ROSA, "#1F5FA8", VINHO, "#C77700"]

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
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
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
/* Os ícones são ligaduras de fonte: em maiúsculas, viram texto */
[data-testid="stSidebar"] [data-testid="stIconMaterial"],
[data-testid="stSidebar"] span[role="img"] {
    color: #000000;
    letter-spacing: 0;
    text-transform: none;
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
[data-testid="stHeader"] {
    height: 2.75rem !important;
    min-height: 2.75rem !important;
    background: #FFFFFF;
}
[data-testid="stLayoutWrapper"]:has(> .st-key-trilha) {
    position: sticky;
    top: 2.75rem;
    z-index: 100;
    box-sizing: border-box;
    width: calc(100% + var(--margem) * 2);
    max-width: none;
    margin: 0 calc(var(--margem) * -1);
    padding: 0 var(--margem) 12px;
    border-bottom: 1px solid #FE0B5D;
    background: #FFFFFF;
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
[data-testid="stMainBlockContainer"] {
    --margem: 2rem;
    max-width: none;
    padding: 2.75rem var(--margem) 4rem;
}
@media (max-width: 640px) {
    [data-testid="stMainBlockContainer"] {
        --margem: 1rem;
    }
}
[data-testid="stMain"] h1,
[data-testid="stMain"] h2 {
    font-family: "Spectral", serif;
    font-weight: 300;
}
.capa {
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    min-height: 440px;
    box-sizing: border-box;
    margin: 0 calc(var(--margem) * -1);
    padding: 2rem var(--margem);
    background: #FE0B5D;
    color: #000000;
}
.capa img {
    position: absolute;
    top: -120px;
    right: -80px;
}
.capa h1 {
    position: relative;
    margin: 0;
    padding: 0;
    color: #000000;
    font-family: "Spectral", serif;
    font-size: clamp(2.75rem, 7vw, 6.5rem);
    font-weight: 300;
    line-height: 1.02;
    letter-spacing: 0.04em;
}
.capa p {
    position: relative;
    margin: 1rem 0 0;
    font-size: 1.125rem;
}
.faixa {
    display: flex;
    gap: 3rem;
    overflow: hidden;
    margin: 0 calc(var(--margem) * -1);
    padding: 0.8rem var(--margem);
    border-bottom: 1px solid #FE0B5D;
    font-size: 15px;
    letter-spacing: 0.38em;
    white-space: nowrap;
}
.faixa span {
    display: inline-flex;
    flex: none;
    align-items: center;
    gap: 1.5rem;
}
/* Cards da mesma linha com a mesma altura e o botão sempre no rodapé */
[data-testid="stHorizontalBlock"]:has([class*="st-key-card_anuncio_"]) {
    align-items: stretch;
}
[data-testid="stColumn"]:has([class*="st-key-card_anuncio_"]) > [data-testid="stVerticalBlock"],
[data-testid="stColumn"]:has([class*="st-key-card_anuncio_"]) [data-testid="stLayoutWrapper"] {
    height: 100%;
}
[class*="st-key-card_anuncio_"] {
    height: 100%;
    gap: 0;
    padding: 0 0 1rem;
}
[class*="st-key-card_anuncio_"] > [data-testid="stElementContainer"]:not(:has(.card-tipo, .sem-foto, [data-testid="stImage"])) {
    box-sizing: border-box;
    padding: 0.5rem 1rem 0;
}
[class*="st-key-card_anuncio_"] > [data-testid="stElementContainer"]:has([data-testid="stPageLink"]) {
    margin-top: auto;
}
[class*="st-key-card_anuncio_"] [data-testid="stImage"],
[class*="st-key-card_anuncio_"] [data-testid="stImageContainer"] {
    width: 100%;
}
.card-tipo {
    padding: 0.5rem 1rem;
    background: #FCEBF2;
    font-size: 12px;
    letter-spacing: 0.3em;
    text-transform: uppercase;
}
.sem-foto {
    display: flex;
    align-items: center;
    justify-content: center;
    aspect-ratio: 1 / 1;
}
.sem-foto.grande {
    flex-direction: column;
    gap: 1rem;
    aspect-ratio: auto;
    min-height: 440px;
    background: #FE0B5D;
    font-size: 13px;
    letter-spacing: 0.3em;
}
[class*="st-key-card_anuncio_"] [data-testid="stImage"] img {
    display: block;
    width: 100%;
    aspect-ratio: 1 / 1;
    object-fit: cover;
}
[class*="st-key-card_anuncio_"] a {
    justify-content: center;
    border: 1px solid #FE0B5D;
    border-radius: 0;
}
</style>
"""


# No celular, o Streamlit deixa o menu aberto ao carregar e ao usar st.page_link, cobrindo a página
_FECHAR_MENU_NO_CELULAR = """
<script>
if (!window.brechoFecharMenu) {
    window.brechoFecharMenu = () => {
        if (window.innerWidth < 768) {
            document.querySelector('[data-testid="stSidebarCollapseButton"] button')?.click();
        }
    };
    setTimeout(window.brechoFecharMenu, 800);
    document.addEventListener("click", (e) => {
        if (e.target.closest('[data-testid="stSidebar"] a')) {
            window.brechoFecharMenu();
        }
    });
}
</script>
"""


def sol_svg(tamanho=144, cor=ROSA):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" aria-hidden="true" width="{tamanho}" height="{tamanho}" viewBox="0 0 100 100" '
        f'fill="{cor}" stroke="{cor}" stroke-width="1.5" stroke-linejoin="round">'
        f'<path d="{_SOL}"></path></svg>'
    )


def sol_html(tamanho=144, cor=ROSA):
    """Sol como imagem: st.html remove tags <svg> ao sanitizar o conteúdo."""
    dados = base64.b64encode(sol_svg(tamanho, cor).encode()).decode()
    return f'<img alt="" width="{tamanho}" height="{tamanho}" src="data:image/svg+xml;base64,{dados}">'


def aplicar_estilo():
    px.defaults.color_discrete_sequence = CORES_GRAFICOS  # o tema não alcança as pizzas
    st.html(_CSS)
    st.html(_FECHAR_MENU_NO_CELULAR, unsafe_allow_javascript=True)
