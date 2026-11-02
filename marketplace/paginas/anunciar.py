"""Página Anunciar: cria categoria, item, tags, anúncio e fotos."""
import streamlit as st

from ..auth import require_login
from ..config import ESTADOS, TIPOS
from ..erros import ErroAplicacao
from ..services import anuncios


def pagina_anunciar():
    user = require_login()
    st.header(":material/sell: Criar anúncio")

    cats = anuncios.listar_categorias()
    with st.expander(":material/add: Nova categoria"):
        with st.form("nova_categoria", clear_on_submit=True):
            nome_cat = st.text_input("Nome da categoria")
            pai = st.selectbox("Categoria pai (opcional)", [""] + list(cats["nome_categoria"]))
            if st.form_submit_button("Criar") and nome_cat.strip():
                try:
                    anuncios.criar_categoria(nome_cat, pai)
                    st.rerun()
                except ErroAplicacao as e:
                    st.error(str(e))

    if cats.empty:
        st.info("Crie ao menos uma categoria para poder anunciar.")
        return

    tipo = st.radio("Tipo de anúncio", TIPOS, horizontal=True)

    with st.form("novo_anuncio", clear_on_submit=True):
        st.subheader("Anúncio")
        titulo = st.text_input("Título")
        descricao = st.text_area("Descrição do anúncio")
        c1, c2 = st.columns(2)
        preco = c1.number_input("Preço (R$)", min_value=0.0, step=1.0)
        prazo = c2.number_input(
            "Prazo do empréstimo (dias)", min_value=1, step=1,
            disabled=(tipo != "Empréstimo"),
        )
        fotos = st.file_uploader(
            "Fotos (até 5, em JPG, PNG ou WebP, com até 5 MB cada)",
            type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True,
        )

        st.subheader("Item")
        item = st.text_input("Nome do item")
        c3, c4 = st.columns(2)
        marca = c3.text_input("Marca")
        estado = c4.selectbox("Estado", ESTADOS)
        categoria = st.selectbox("Categoria", list(cats["nome_categoria"]))
        descricao_item = st.text_area("Descrição do item")
        tags = st.text_input("Tags (separadas por vírgula)")
        reestocavel = st.checkbox("Item reestocável")

        if st.form_submit_button("Publicar", width="stretch"):
            dados = {
                "titulo": titulo.strip(), "descricao": descricao.strip(),
                "preco": preco, "tipo": tipo, "prazo": int(prazo),
                "fotos": [f.getvalue() for f in fotos],
                "item": item.strip(), "marca": marca.strip(), "estado": estado,
                "categoria": categoria, "descricao_item": descricao_item.strip(),
                "reestocavel": reestocavel,
                "tags": tags.split(","),
            }
            try:
                novo = anuncios.criar_anuncio(user["cpf"], dados)
                st.success(f"Anúncio #{novo} publicado!")
            except ErroAplicacao as e:
                st.error(str(e))
