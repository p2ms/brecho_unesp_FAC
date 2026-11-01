"""Página Busca avançada: filtros combinados montados em SQL."""
import psycopg2
import streamlit as st

from ..config import ESTADOS, TIPOS
from ..db import db_error, query_df
from ..services import listar_categorias


def pagina_busca():
    st.header("🔍 Busca avançada")
    st.caption(
        "Combine filtros de várias tabelas: a busca junta anúncio, item, categoria "
        "(com subcategorias), tags, vendedor e avaliações."
    )

    cats = listar_categorias()
    tags_df = query_df("SELECT nome_tag FROM tag ORDER BY 1")
    pmax = float(query_df("SELECT COALESCE(MAX(preco), 0)::float AS m FROM anuncio").iloc[0]["m"])
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
    ordens = {
        "Mais recentes": "a.data_hora_publicacao DESC",
        "Menor preço": "a.preco ASC",
        "Maior preço": "a.preco DESC",
        "Melhor avaliados": "nota_vendedor DESC, avaliacoes DESC",
        "Mais comentados": "comentarios DESC",
    }
    ordem = c9.selectbox("Ordenar por", list(ordens))

    params = []
    with_sql = ""
    if categoria:
        with_sql = """WITH RECURSIVE cat AS (
                          SELECT nome_categoria FROM categoria WHERE nome_categoria = %s
                          UNION ALL
                          SELECT c.nome_categoria FROM categoria c
                          JOIN cat ON c.nome_categoria_pai = cat.nome_categoria
                      ),"""
        params.append(categoria)
        nota_cte = "nota AS"
    else:
        with_sql = "WITH"
        nota_cte = "nota AS"

    sql = f"""
        {with_sql}
        {nota_cte} (
            SELECT cpf_avaliado, AVG(nota)::float AS nota_media, COUNT(*) AS n
            FROM avaliacao GROUP BY cpf_avaliado
        )
        SELECT a.id_anuncio AS id, a.titulo, a.tipo, a.preco::float AS preco,
               i.nome AS item, i.marca, i.estado, i.nome_categoria AS categoria,
               u.nome AS vendedor,
               COALESCE(n.nota_media, 0) AS nota_vendedor,
               COALESCE(n.n, 0) AS avaliacoes,
               (SELECT COUNT(*) FROM comentario c WHERE c.id_anuncio = a.id_anuncio) AS comentarios,
               (SELECT string_agg(t.nome_tag, ', ') FROM item_tag t
                 WHERE t.id_item = i.id_item) AS tags,
               a.data_hora_publicacao AS publicado_em
        FROM anuncio a
        JOIN item i ON i.id_item = a.id_item
        JOIN usuario u ON u.cpf = a.cpf_vendedor
        LEFT JOIN nota n ON n.cpf_avaliado = a.cpf_vendedor
        WHERE a.status = 'Disponível' AND a.preco BETWEEN %s AND %s
    """
    params += [faixa[0], faixa[1]]

    if categoria:
        sql += " AND i.nome_categoria IN (SELECT nome_categoria FROM cat)"
    if texto.strip():
        sql += " AND (a.titulo ILIKE %s OR i.nome ILIKE %s OR i.marca ILIKE %s)"
        params += [f"%{texto.strip()}%"] * 3
    if tags:
        sql += """ AND (SELECT COUNT(DISTINCT t.nome_tag) FROM item_tag t
                        WHERE t.id_item = i.id_item AND t.nome_tag = ANY(%s)) = %s"""
        params += [tags, len(tags)]
    if estados:
        sql += " AND i.estado = ANY(%s)"
        params.append(estados)
    if tipo != "Todos":
        sql += " AND a.tipo = %s"
        params.append(tipo)
    if nota_min > 0:
        sql += " AND COALESCE(n.nota_media, 0) >= %s"
        params.append(nota_min)
    if dias > 0:
        sql += " AND a.data_hora_publicacao >= now() - make_interval(days => %s)"
        params.append(int(dias))
    sql += f" ORDER BY {ordens[ordem]}"

    try:
        df = query_df(sql, params)
    except psycopg2.Error as e:
        db_error(e)
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
                "nota_vendedor": st.column_config.NumberColumn("nota vendedor", format="%.1f ⭐"),
            },
        )
        with st.expander("Ver SQL gerado"):
            st.code(sql, language="sql")
    else:
        st.info("Nenhum anúncio encontrado com esses filtros.")
