"""Página Mensagens: caixa de entrada por anúncio."""
import streamlit as st

from ..auth import require_login
from ..components import chat
from ..services import interacoes


def pagina_mensagens():
    user = require_login()
    st.header("✉️ Mensagens")
    convs = interacoes.listar_conversas(user["cpf"])
    if convs.empty:
        st.info("Você ainda não tem conversas.")
        return
    idx = st.selectbox(
        "Conversa", range(len(convs)),
        format_func=lambda i: f"{convs.iloc[i]['titulo']} — {convs.iloc[i]['outro_nome']}",
    )
    c = convs.iloc[idx]
    chat(int(c["id_anuncio"]), user["cpf"], c["outro_cpf"].strip(), key=f"inbox_{idx}")
