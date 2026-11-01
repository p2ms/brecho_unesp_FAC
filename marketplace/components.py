"""Componentes de interface reutilizados por mais de uma página."""
import pandas as pd
import psycopg2
import streamlit as st

from .auth import current_user
from .db import db_error, execute, query_df


def chat(id_anuncio, meu_cpf, outro_cpf, key):
    msgs = query_df(
        """SELECT m.cpf_remetente, m.texto, m.data_hora, u.nome
           FROM mensagem m JOIN usuario u ON u.cpf = m.cpf_remetente
           WHERE m.id_anuncio = %s
             AND ((m.cpf_remetente = %s AND m.cpf_destinatario = %s)
               OR (m.cpf_remetente = %s AND m.cpf_destinatario = %s))
           ORDER BY m.data_hora""",
        (id_anuncio, meu_cpf, outro_cpf, outro_cpf, meu_cpf),
    )
    if msgs.empty:
        st.caption("Nenhuma mensagem ainda.")
    for _, m in msgs.iterrows():
        papel = "user" if m["cpf_remetente"].strip() == meu_cpf else "assistant"
        with st.chat_message(papel):
            st.caption(f"{m['nome']} · {m['data_hora']:%d/%m/%Y %H:%M}")
            st.write(m["texto"])

    with st.form(f"form_chat_{key}", clear_on_submit=True):
        texto = st.text_area("Nova mensagem", height=80)
        if st.form_submit_button("Enviar") and texto.strip():
            try:
                execute(
                    """INSERT INTO mensagem (cpf_remetente, cpf_destinatario, id_anuncio, texto)
                       VALUES (%s, %s, %s, %s)""",
                    (meu_cpf, outro_cpf, id_anuncio, texto.strip()),
                )
                st.rerun()
            except psycopg2.Error as e:
                db_error(e)


def comentarios(id_anuncio):
    df = query_df(
        """SELECT c.texto, c.data_hora, u.nome
           FROM comentario c JOIN usuario u ON u.cpf = c.cpf_comentador
           WHERE c.id_anuncio = %s ORDER BY c.data_hora DESC""",
        (id_anuncio,),
    )
    user = current_user()
    if user:
        with st.form(f"form_coment_{id_anuncio}", clear_on_submit=True):
            texto = st.text_area("Comentar", height=80)
            if st.form_submit_button("Publicar comentário") and texto.strip():
                try:
                    execute(
                        """INSERT INTO comentario (cpf_comentador, id_anuncio, texto)
                           VALUES (%s, %s, %s)""",
                        (user["cpf"], id_anuncio, texto.strip()),
                    )
                    st.rerun()
                except psycopg2.Error as e:
                    db_error(e)
    else:
        st.caption("Entre na sua conta para comentar.")

    if df.empty:
        st.caption("Sem comentários ainda.")
    for _, c in df.iterrows():
        with st.container(border=True):
            st.caption(f"{c['nome']} · {c['data_hora']:%d/%m/%Y %H:%M}")
            st.write(c["texto"])


def card_preco(a):
    if a["tipo"] == "Empréstimo":
        prazo = int(a["prazo"]) if pd.notna(a["prazo"]) else "?"
        return f"R$ {a['preco']:.2f} · empréstimo por {prazo} dia(s)"
    return f"R$ {a['preco']:.2f}"
