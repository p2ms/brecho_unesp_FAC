"""Sessão do usuário: login, cadastro e controle de acesso."""
from datetime import date, timedelta

import psycopg2
import streamlit as st

from .db import db_error, execute, query_df


def current_user():
    return st.session_state.get("user")


def require_login():
    if current_user() is None:
        st.warning("Entre na sua conta (menu lateral) para acessar esta página.")
        st.stop()
    return current_user()


def sidebar_conta():
    with st.sidebar:
        st.title("🔁 Marketplace")
        user = current_user()
        if user:
            st.write(f"Olá, **{user['nome']}** 👋")
            if st.button("Sair", width="stretch"):
                del st.session_state["user"]
                st.rerun()
            return

        modo = st.radio("Conta", ["Entrar", "Cadastrar"], horizontal=True)
        if modo == "Entrar":
            email = st.text_input("E-mail")
            if st.button("Entrar", width="stretch"):
                df = query_df("SELECT * FROM usuario WHERE email = %s", (email.strip(),))
                if df.empty:
                    st.error("E-mail não encontrado.")
                else:
                    u = df.iloc[0].to_dict()
                    u["cpf"] = u["cpf"].strip()
                    st.session_state["user"] = u
                    st.rerun()
        else:
            limite = date.today() - timedelta(days=16 * 365 + 4)
            with st.form("cadastro"):
                cpf = st.text_input("CPF (11 dígitos, só números)", max_chars=11)
                nome = st.text_input("Nome")
                email = st.text_input("E-mail")
                nasc = st.date_input(
                    "Data de nascimento", value=limite,
                    min_value=date(1920, 1, 1), max_value=limite,
                )
                if st.form_submit_button("Cadastrar", width="stretch"):
                    if not (cpf.isdigit() and len(cpf) == 11):
                        st.error("CPF deve ter 11 dígitos.")
                    elif not nome.strip() or not email.strip():
                        st.error("Preencha nome e e-mail.")
                    else:
                        try:
                            execute(
                                """INSERT INTO usuario (cpf, nome, email, data_nascimento)
                                   VALUES (%s, %s, %s, %s)""",
                                (cpf, nome.strip(), email.strip(), nasc),
                            )
                            st.success("Cadastro feito! Agora é só entrar.")
                        except psycopg2.Error as e:
                            db_error(e)
