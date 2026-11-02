"""As páginas do app, cada uma com seu endereço."""
import streamlit as st

from .paginas.anunciar import pagina_anunciar
from .paginas.conta import pagina_conta
from .paginas.dashboard import pagina_dashboard
from .paginas.loja import pagina_anuncio, pagina_loja
from .paginas.mensagens import pagina_mensagens
from .paginas.meus_anuncios import pagina_minha_loja


def criar_paginas():
    return {
        "loja": st.Page(pagina_loja, title="Loja", default=True),
        "anuncio": st.Page(pagina_anuncio, title="Anúncio", url_path="anuncio"),
        "anunciar": st.Page(pagina_anunciar, title="Anunciar", url_path="anunciar"),
        "minha_loja": st.Page(pagina_minha_loja, title="Minha loja", url_path="minha-loja"),
        "mensagens": st.Page(pagina_mensagens, title="Mensagens", url_path="mensagens"),
        "painel": st.Page(pagina_dashboard, title="Painel", url_path="painel"),
        "conta": st.Page(pagina_conta, title="Minha conta", url_path="minha-conta"),
    }
