"""Sessão do usuário: login, cadastro e controle de acesso."""
from datetime import date, timedelta

import streamlit as st

from .erros import ErroAplicacao
from .services import usuarios


def current_user():
    return st.session_state.get("user")


def require_login():
    if current_user() is None:
        st.warning("Entre na sua conta (menu lateral) para acessar esta página.")
        st.stop()
    return current_user()


def sidebar_conta():
    with st.sidebar:
        st.title("Brechó da Unesp")
        user = current_user()
        if user:
            st.write(f"Olá, **{user['nome']}** :material/waving_hand:")
            if st.button("Sair", width="stretch"):
                del st.session_state["user"]
                st.rerun()
            return

        modo = st.radio("Conta", ["Entrar", "Cadastrar"], horizontal=True)
        if modo == "Entrar":
            email = st.text_input("E-mail")
            if st.button("Entrar", width="stretch"):
                u = usuarios.buscar_por_email(email)
                if u is None:
                    st.error("E-mail não encontrado.")
                else:
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
                    try:
                        usuarios.cadastrar(cpf, nome, email, nasc)
                        st.success("Cadastro feito! Agora é só entrar.")
                    except ErroAplicacao as e:
                        st.error(str(e))
