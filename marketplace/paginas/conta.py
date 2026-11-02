"""Página Minha conta: login e cadastro, ou compras, vendas e perfil de quem entrou."""
import streamlit as st

from ..auth import current_user, formulario_login
from ..navegacao import trilha
from .perfil import pagina_perfil
from .transacoes import pagina_compras, pagina_vendas

ABAS = {
    "compras": ("Compras", pagina_compras),
    "vendas": ("Vendas", pagina_vendas),
    "perfil": ("Perfil", pagina_perfil),
}


def pagina_conta():
    user = current_user()
    if user is None:
        trilha("MINHA CONTA")
        st.header("Minha conta")
        formulario_login()
        return

    aba = st.query_params.get("aba", "compras")
    if aba not in ABAS:
        aba = "compras"
    trilha(("MINHA CONTA", "conta"), ABAS[aba][0].upper())

    c1, c2 = st.columns([6, 1], vertical_alignment="center")
    c1.header(user["nome"])
    c1.caption(user["email"])
    if c2.button("Sair", width="stretch"):
        del st.session_state["user"]
        st.rerun()

    escolha = st.segmented_control(
        "Seção", list(ABAS), default=aba, required=True, label_visibility="collapsed",
        format_func=lambda a: ABAS[a][0],
    )
    if escolha != aba:
        st.query_params["aba"] = escolha
        st.rerun()
    ABAS[aba][1]()
