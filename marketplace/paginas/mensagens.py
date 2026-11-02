"""Página Mensagens: caixa de entrada por anúncio."""
import streamlit as st

from ..auth import require_login
from ..components import chat
from ..navegacao import trilha
from ..services import interacoes


def pagina_mensagens():
    trilha("MENSAGENS")
    user = require_login()
    st.header(":material/mail: Mensagens")
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
