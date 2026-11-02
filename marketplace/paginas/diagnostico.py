"""Diagnóstico exibido quando o banco não tem as tabelas do marketplace."""
import streamlit as st

from ..config import TABELAS_ESPERADAS
from ..erros import ErroAplicacao
from ..services import diagnostico


def diagnostico_tabelas():
    st.error("O app conectou ao banco, mas não encontrou as tabelas do marketplace nele.")
    try:
        info = diagnostico.info_conexao()
        tabs = diagnostico.listar_tabelas()
    except ErroAplicacao as e:
        st.error(str(e))
        return

    st.markdown(
        f"**Onde o app está conectado** (compare com o painel do Supabase):\n\n"
        f"- Host: `{info['host']}`\n- Banco: `{info['banco']}`\n"
        f"- Usuário: `{info['usuario']}`\n- Esquema padrão: `{info['esquema']}`"
    )
    if tabs.empty:
        st.warning(
            "Este banco está **vazio**. Rode o `schema.sql` (e depois o `seed.sql`) no SQL Editor "
            "do Supabase, **no mesmo projeto e banco** acima."
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
