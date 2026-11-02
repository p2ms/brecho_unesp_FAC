"""Página Busca avançada: filtros combinados de várias tabelas."""
import streamlit as st

from ..config import ESTADOS, TIPOS
from ..erros import ErroAplicacao
from ..navegacao import trilha
from ..services import anuncios


def pagina_busca():
    trilha(("LOJA", "loja"), "BUSCA AVANÇADA")
    st.header(":material/search: Busca avançada")
    st.caption(
        "Combine filtros de várias tabelas: a busca junta anúncio, item, categoria "
        "(com subcategorias), tags, vendedor e avaliações."
    )

    cats = anuncios.listar_categorias()
    tags_df = anuncios.listar_tags()
    pmax = anuncios.preco_maximo()
    pmax = pmax if pmax > 0 else 100.0

    c1, c2, c3 = st.columns(3)
    texto = c1.text_input("Texto (título, item ou marca)")
    categoria = c2.selectbox("Categoria (inclui subcategorias)", [""] + list(cats["nome_categoria"]))
    tags = c3.multiselect("Tags (o item precisa ter todas)", list(tags_df["nome_tag"]))

    c4, c5, c6 = st.columns(3)
    estados = c4.multiselect("Estado do item", ESTADOS)
    tipo = c5.selectbox("Tipo", ["Todos"] + TIPOS)
    nota_min = c6.slider("Nota mínima do vendedor", 0.0, 5.0, 0.0, 0.5)

    c7, c8, c9 = st.columns(3)
    faixa = c7.slider("Faixa de preço (R$)", 0.0, pmax, (0.0, pmax))
    dias = c8.number_input("Publicados nos últimos N dias (0 = qualquer)", 0, 3650, 0)
    ordem = c9.selectbox("Ordenar por", list(anuncios.ORDENS_BUSCA))

    try:
        df, sql = anuncios.busca_avancada(
            texto=texto, categoria=categoria, tags=tags, estados=estados, tipo=tipo,
            nota_min=nota_min, faixa=faixa, dias=dias, ordem=ordem,
        )
    except ErroAplicacao as e:
        st.error(str(e))
        return

    m1, m2, m3 = st.columns(3)
    m1.metric("Resultados", len(df))
    if not df.empty:
        m2.metric("Preço médio", f"R$ {df['preco'].mean():,.2f}")
        m3.metric("Mediana", f"R$ {df['preco'].median():,.2f}")
        st.dataframe(
            df, width="stretch", hide_index=True,
            column_config={
                "preco": st.column_config.NumberColumn("preço", format="R$ %.2f"),
                "nota_vendedor": st.column_config.NumberColumn("nota vendedor", format="%.1f ★"),
            },
        )
        with st.expander("Ver SQL gerado"):
            st.code(sql, language="sql")
    else:
        st.info("Nenhum anúncio encontrado com esses filtros.")
