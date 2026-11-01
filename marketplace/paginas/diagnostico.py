"""Diagnóstico exibido quando o banco não tem as tabelas do marketplace."""
from urllib.parse import urlparse

import psycopg2
import streamlit as st

from ..config import DATABASE_URL, TABELAS_ESPERADAS
from ..db import db_error, query_df


def diagnostico_tabelas():
    st.error("O app conectou ao banco, mas não encontrou as tabelas do marketplace nele.")
    try:
        info = query_df(
            "SELECT current_database() AS banco, current_user AS usuario, current_schema() AS esquema"
        ).iloc[0]
        tabs = query_df(
            """SELECT table_schema AS esquema, table_name AS tabela
               FROM information_schema.tables
               WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
               ORDER BY 1, 2"""
        )
    except psycopg2.Error as e:
        db_error(e)
        return

    host = urlparse(DATABASE_URL).hostname
    st.markdown(
        f"**Onde o app está conectado** (compare com o painel do Neon):\n\n"
        f"- Host: `{host}`\n- Banco: `{info['banco']}`\n"
        f"- Usuário: `{info['usuario']}`\n- Esquema padrão: `{info['esquema']}`"
    )
    if tabs.empty:
        st.warning(
            "Este banco está **vazio**. Rode o `schema.sql` (e depois o `seed.sql`) no SQL Editor "
            "do Neon, **no mesmo branch e banco** acima."
        )
        return

    st.write("Tabelas que o app enxerga neste banco:")
    st.dataframe(tabs, hide_index=True, width="stretch")
    no_public = set(tabs.loc[tabs["esquema"] == "public", "tabela"])
    faltam = [t for t in TABELAS_ESPERADAS if t not in no_public]
    if faltam:
        st.warning("Faltam no esquema `public`: " + ", ".join(f"`{t}`" for t in faltam))
        fora = tabs[(tabs["esquema"] != "public") & (tabs["tabela"].isin(faltam))]
        if not fora.empty:
            st.info(
                "Algumas dessas tabelas existem em OUTRO esquema (veja a lista acima). "
                "Recrie-as no esquema `public` com o `schema.sql`."
            )
