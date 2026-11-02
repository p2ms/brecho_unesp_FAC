"""Ponto de entrada do Streamlit: configuração da página, menu lateral e navegação."""
import streamlit as st

from marketplace.config import DATABASE_URL, ENV_PATH
from marketplace.erros import ErroAplicacao, TabelaAusente
from marketplace.estilo import aplicar_estilo, sol_svg
from marketplace.menu import menu
from marketplace.navegacao import registrar
from marketplace.paginas.diagnostico import diagnostico_tabelas
from marketplace.rotas import criar_paginas

paginas = criar_paginas()
registrar(paginas)
atual = st.navigation(list(paginas.values()), position="hidden")

# Depois de st.navigation, que trocaria o título da aba pelo nome da página
st.set_page_config(page_title="Brechó da Unesp", page_icon=sol_svg(64), layout="wide")
aplicar_estilo()

if not DATABASE_URL:
    st.error("Dados de conexão com o banco não encontrados (DATABASE_URL ou DB_HOST/DB_USER/...).")
    st.markdown(
        f"""
**O que verificar:**
1. Existe um arquivo chamado exatamente `.env` (não `.env.example`, nem `.env.txt`) nesta pasta?
   `{ENV_PATH.parent}` → arquivo `.env` encontrado: **{"sim" if ENV_PATH.exists() else "NÃO"}**
2. Dentro dele há `DATABASE_URL=postgresql://usuario:senha@host/banco?sslmode=require`
   **ou** as variáveis `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` e `DB_PORT`
   (sem espaços em volta do `=`).
3. Depois de salvar o arquivo, pare o Streamlit (Ctrl+C) e rode `streamlit run app.py` de novo.

Publicado no Streamlit Cloud? Defina `DATABASE_URL` em *Settings → Secrets*.
"""
    )
    st.stop()

try:
    menu(next(nome for nome, p in paginas.items() if p.url_path == atual.url_path))
    atual.run()
except TabelaAusente:
    diagnostico_tabelas()
except ErroAplicacao as e:
    st.error(str(e))
