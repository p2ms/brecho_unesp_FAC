"""Página Perfil: dados do usuário, nota média e cartões."""
import pandas as pd
import psycopg2
import streamlit as st

from ..auth import require_login
from ..db import db_error, execute, query_df


def pagina_perfil():
    user = require_login()
    st.header("👤 Meu perfil")

    atual = query_df("SELECT * FROM usuario WHERE cpf = %s", (user["cpf"],)).iloc[0].to_dict()
    atual = {k: (None if pd.isna(v) else v) for k, v in atual.items()}
    media = query_df(
        "SELECT AVG(nota)::float AS media, COUNT(*) AS qtd FROM avaliacao WHERE cpf_avaliado = %s",
        (user["cpf"],),
    ).iloc[0]

    c1, c2 = st.columns([1, 3])
    with c1:
        if atual["foto"]:
            st.image(atual["foto"], width="stretch")
        else:
            st.markdown("# 🙂")
    with c2:
        st.subheader(atual["nome"])
        st.caption(atual["email"])
        if media["qtd"]:
            st.write(f"⭐ **{media['media']:.1f}** ({int(media['qtd'])} avaliações)")
        else:
            st.write("Sem avaliações ainda.")

    with st.form("editar_perfil"):
        nome = st.text_input("Nome", value=atual["nome"])
        foto = st.text_input("URL da foto", value=atual["foto"] or "")
        bio = st.text_area("Bio", value=atual["bio"] or "")
        if st.form_submit_button("Salvar"):
            try:
                execute(
                    "UPDATE usuario SET nome = %s, foto = %s, bio = %s WHERE cpf = %s",
                    (nome.strip(), foto.strip() or None, bio.strip() or None, user["cpf"]),
                )
                st.session_state["user"]["nome"] = nome.strip()
                st.success("Perfil atualizado!")
                st.rerun()
            except psycopg2.Error as e:
                db_error(e)

    st.subheader("💳 Meus cartões")
    cartoes = query_df("SELECT numero, metodo FROM cartao WHERE cpf = %s", (user["cpf"],))
    if cartoes.empty:
        st.caption("Nenhum cartão cadastrado.")
    else:
        cartoes["numero"] = "•••• " + cartoes["numero"].str[-4:]
        st.dataframe(cartoes, width="stretch", hide_index=True)

    with st.form("novo_cartao", clear_on_submit=True):
        numero = st.text_input("Número do cartão (13 a 19 dígitos)", max_chars=19)
        metodo = st.selectbox("Tipo", ["Crédito", "Débito"])
        if st.form_submit_button("Adicionar cartão"):
            try:
                execute(
                    "INSERT INTO cartao (cpf, numero, metodo) VALUES (%s, %s, %s)",
                    (user["cpf"], numero.strip(), metodo),
                )
                st.rerun()
            except psycopg2.Error as e:
                db_error(e)
