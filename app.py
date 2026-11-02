"""Ponto de entrada do Streamlit: configuração da página, menu lateral e navegação."""
import streamlit as st

from marketplace.auth import sidebar_conta
from marketplace.config import DATABASE_URL, ENV_PATH
from marketplace.erros import ErroAplicacao, TabelaAusente
from marketplace.paginas.anunciar import pagina_anunciar
from marketplace.paginas.busca import pagina_busca
from marketplace.paginas.dashboard import pagina_dashboard
from marketplace.paginas.diagnostico import diagnostico_tabelas
from marketplace.paginas.loja import pagina_loja
from marketplace.paginas.mensagens import pagina_mensagens
from marketplace.paginas.perfil import pagina_perfil
from marketplace.paginas.transacoes import pagina_compras, pagina_vendas

st.set_page_config(page_title="Marketplace", page_icon="🔁", layout="wide")

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


# ---------------------------------------------------------------
# Navegação
# ---------------------------------------------------------------
sidebar_conta()

PAGINAS = {
    "🛍️ Loja": pagina_loja,
    "🔍 Busca avançada": pagina_busca,
    "💰 Anunciar": pagina_anunciar,
    "✉️ Mensagens": pagina_mensagens,
    "📦 Minhas compras": pagina_compras,
    "💼 Minhas vendas": pagina_vendas,
    "👤 Perfil": pagina_perfil,
    "📊 Dashboard": pagina_dashboard,
}
with st.sidebar:
    st.divider()
    escolha = st.radio("Navegação", list(PAGINAS), label_visibility="collapsed")

try:
    PAGINAS[escolha]()
except TabelaAusente:
    diagnostico_tabelas()
except ErroAplicacao as e:
    st.error(str(e))
