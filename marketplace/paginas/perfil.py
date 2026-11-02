"""Página Perfil: dados do usuário, nota média e cartões."""
import streamlit as st

from ..auth import require_login
from ..components import eh_link
from ..erros import ErroAplicacao
from ..estilo import sol_html
from ..services import usuarios


def pagina_perfil():
    user = require_login()

    atual = usuarios.obter_perfil(user["cpf"])
    media = usuarios.nota_media(user["cpf"])

    c1, c2 = st.columns([1, 3])
    with c1:
        if eh_link(atual["foto"]):
            st.image(atual["foto"], width="stretch")
        else:
            st.html(sol_html(96))
    with c2:
        if media["qtd"]:
            st.write(f"**Nota média:** {media['media']:.1f} ({int(media['qtd'])} avaliações)")
        else:
            st.write("Sem avaliações ainda.")

    with st.form("editar_perfil"):
        nome = st.text_input("Nome", value=atual["nome"])
        foto = st.text_input("URL da foto", value=atual["foto"] or "")
        bio = st.text_area("Bio", value=atual["bio"] or "")
        if st.form_submit_button("Salvar", type="primary"):
            try:
                usuarios.atualizar_perfil(user["cpf"], nome, foto, bio)
                st.session_state["user"]["nome"] = nome.strip()
                st.success("Perfil atualizado!")
                st.rerun()
            except ErroAplicacao as e:
                st.error(str(e))

    st.subheader("Meus cartões")
    cartoes = usuarios.listar_cartoes(user["cpf"])
    if cartoes.empty:
        st.caption("Nenhum cartão cadastrado.")
    else:
        st.dataframe(cartoes, width="stretch", hide_index=True)

    with st.form("novo_cartao", clear_on_submit=True):
        numero = st.text_input("Número do cartão (13 a 19 dígitos)", max_chars=19)
        metodo = st.selectbox("Tipo", ["Crédito", "Débito"])
        if st.form_submit_button("Adicionar cartão"):
            try:
                usuarios.adicionar_cartao(user["cpf"], numero, metodo)
                st.rerun()
            except ErroAplicacao as e:
                st.error(str(e))
