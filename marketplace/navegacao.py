"""Acesso às páginas registradas no app e breadcrumb no topo de cada uma."""
import streamlit as st

_CHAVE = "_paginas"


def registrar(paginas):
    st.session_state[_CHAVE] = paginas


def pagina(nome):
    return st.session_state[_CHAVE][nome]


def trilha(*partes):
    """Cada parte é (rótulo, nome da página[, parâmetros]); a última é só o texto de onde se está."""
    with st.container(horizontal=True, key="trilha", vertical_alignment="center"):
        for rotulo, nome, *parametros in partes[:-1]:
            st.page_link(pagina(nome), label=rotulo, query_params=parametros[0] if parametros else None)
            st.text("/")
        st.text(partes[-1])
