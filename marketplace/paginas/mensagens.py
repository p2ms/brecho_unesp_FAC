"""Página Mensagens: caixa de entrada por anúncio."""
import streamlit as st

from ..auth import require_login
from ..components import chat
from ..db import query_df


def pagina_mensagens():
    user = require_login()
    st.header("✉️ Mensagens")
    convs = query_df(
        """SELECT DISTINCT a.id_anuncio, a.titulo, u.cpf AS outro_cpf, u.nome AS outro_nome
           FROM mensagem m
           JOIN anuncio a ON a.id_anuncio = m.id_anuncio
           JOIN usuario u ON u.cpf = CASE WHEN m.cpf_remetente = %s
                                          THEN m.cpf_destinatario ELSE m.cpf_remetente END
           WHERE m.cpf_remetente = %s OR m.cpf_destinatario = %s""",
        (user["cpf"],) * 3,
    )
    if convs.empty:
        st.info("Você ainda não tem conversas.")
        return
    idx = st.selectbox(
        "Conversa", range(len(convs)),
        format_func=lambda i: f"{convs.iloc[i]['titulo']} — {convs.iloc[i]['outro_nome']}",
    )
    c = convs.iloc[idx]
    chat(int(c["id_anuncio"]), user["cpf"], c["outro_cpf"].strip(), key=f"inbox_{idx}")
