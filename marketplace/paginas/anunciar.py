"""Página Anunciar: cria categoria, item, tags, anúncio e fotos."""
import psycopg2
import streamlit as st

from ..auth import require_login
from ..config import ESTADOS, TIPOS
from ..db import db_error, execute, query_df
from ..services import criar_anuncio, listar_categorias


def pagina_anunciar():
    user = require_login()
    st.header("💰 Criar anúncio")

    cats = listar_categorias()
    with st.expander("➕ Nova categoria"):
        with st.form("nova_categoria", clear_on_submit=True):
            nome_cat = st.text_input("Nome da categoria")
            pai = st.selectbox("Categoria pai (opcional)", [""] + list(cats["nome_categoria"]))
            if st.form_submit_button("Criar") and nome_cat.strip():
                try:
                    execute(
                        "INSERT INTO categoria (nome_categoria, nome_categoria_pai) VALUES (%s, %s)",
                        (nome_cat.strip(), pai or None),
                    )
                    st.rerun()
                except psycopg2.Error as e:
                    db_error(e)

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
        fotos = st.text_area("URLs das fotos (uma por linha)")

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
            if not titulo.strip() or not item.strip():
                st.error("Título e nome do item são obrigatórios.")
            else:
                dados = {
                    "titulo": titulo.strip(), "descricao": descricao.strip(),
                    "preco": preco, "tipo": tipo, "prazo": int(prazo),
                    "fotos": [u.strip() for u in fotos.splitlines() if u.strip()],
                    "item": item.strip(), "marca": marca.strip(), "estado": estado,
                    "categoria": categoria, "descricao_item": descricao_item.strip(),
                    "reestocavel": reestocavel,
                    "tags": sorted({t.strip().lower() for t in tags.split(",") if t.strip()}),
                }
                try:
                    novo = criar_anuncio(user["cpf"], dados)
                    st.success(f"Anúncio #{novo} publicado!")
                except psycopg2.Error as e:
                    db_error(e)

    st.subheader("Meus anúncios")
    meus = query_df(
        """SELECT a.id_anuncio AS id, a.titulo, a.tipo, a.preco, a.status,
                  i.nome AS item, a.data_hora_publicacao AS publicado_em
           FROM anuncio a JOIN item i ON i.id_item = a.id_item
           WHERE a.cpf_vendedor = %s ORDER BY a.data_hora_publicacao DESC""",
        (user["cpf"],),
    )
    st.dataframe(meus, width="stretch", hide_index=True)
