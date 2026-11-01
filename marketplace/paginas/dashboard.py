"""Página Dashboard: análises visuais e estatísticas."""
import pandas as pd
import plotly.express as px
import streamlit as st

from ..db import query_df


def _mostrar(col, df, fig_fn):
    if df.empty:
        col.caption("Sem dados para este gráfico.")
    else:
        col.plotly_chart(fig_fn(df), width="stretch")


def pagina_dashboard():
    st.header("📊 Dashboard analítico")
    tab_geral, tab_mercado, tab_usuarios, tab_op = st.tabs(
        ["Visão geral", "Mercado", "Usuários", "Operação"]
    )

    # ---------------- Visão geral ----------------
    with tab_geral:
        kpi = query_df(
            """SELECT
                 (SELECT COUNT(*) FROM usuario) AS usuarios,
                 (SELECT COUNT(*) FROM anuncio WHERE status = 'Disponível') AS disponiveis,
                 (SELECT COUNT(*) FROM transacao WHERE status = 'Concluída') AS concluidas,
                 (SELECT COALESCE(SUM(valor), 0)::float FROM transacao
                   WHERE status = 'Concluída') AS volume"""
        ).iloc[0]
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Usuários", int(kpi["usuarios"]))
        k2.metric("Anúncios disponíveis", int(kpi["disponiveis"]))
        k3.metric("Transações concluídas", int(kpi["concluidas"]))
        k4.metric("Volume transacionado", f"R$ {float(kpi['volume']):,.2f}")

        c1, c2 = st.columns(2)
        _mostrar(
            c1,
            query_df(
                """SELECT i.nome_categoria AS categoria, COUNT(*) AS anuncios
                   FROM anuncio a JOIN item i ON i.id_item = a.id_item
                   GROUP BY 1 ORDER BY 2 DESC"""
            ),
            lambda d: px.bar(d, x="categoria", y="anuncios", title="Anúncios por categoria"),
        )
        _mostrar(
            c2,
            query_df("SELECT status, COUNT(*) AS qtd FROM anuncio GROUP BY 1"),
            lambda d: px.pie(d, names="status", values="qtd", title="Anúncios por status"),
        )

        _mostrar(
            st,
            query_df(
                """WITH semanal AS (
                       SELECT date_trunc('week', data_hora_publicacao)::date AS semana,
                              COUNT(*) AS anuncios
                       FROM anuncio GROUP BY 1)
                   SELECT semana, anuncios,
                          AVG(anuncios) OVER (ORDER BY semana
                              ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)::float AS media_movel_3_semanas
                   FROM semanal ORDER BY semana"""
            ),
            lambda d: px.line(
                d, x="semana", y=["anuncios", "media_movel_3_semanas"], markers=True,
                title="Anúncios publicados por semana (com média móvel)",
            ),
        )

    # ---------------- Mercado ----------------
    with tab_mercado:
        c1, c2 = st.columns(2)
        _mostrar(
            c1,
            query_df(
                """WITH RECURSIVE arv AS (
                       SELECT nome_categoria, nome_categoria AS raiz
                       FROM categoria WHERE nome_categoria_pai IS NULL
                       UNION ALL
                       SELECT c.nome_categoria, arv.raiz
                       FROM categoria c JOIN arv ON c.nome_categoria_pai = arv.nome_categoria)
                   SELECT arv.raiz AS categoria_raiz, COUNT(*) AS anuncios,
                          AVG(a.preco)::float AS preco_medio
                   FROM anuncio a
                   JOIN item i ON i.id_item = a.id_item
                   JOIN arv ON arv.nome_categoria = i.nome_categoria
                   WHERE a.tipo = 'Venda'
                   GROUP BY 1 ORDER BY 3 DESC"""
            ),
            lambda d: px.bar(
                d, x="categoria_raiz", y="preco_medio", hover_data=["anuncios"],
                title="Preço médio por categoria raiz (inclui subcategorias)",
            ),
        )
        _mostrar(
            c2,
            query_df(
                """SELECT i.estado, a.preco::float AS preco
                   FROM anuncio a JOIN item i ON i.id_item = a.id_item
                   WHERE a.tipo = 'Venda'"""
            ),
            lambda d: px.box(d, x="estado", y="preco", points="all",
                             title="Distribuição de preços por estado do item"),
        )

        c3, c4 = st.columns(2)

        def heat(d):
            pivot = d.pivot_table(index="categoria", columns="estado", values="qtd", fill_value=0)
            return px.imshow(pivot, text_auto=True, aspect="auto",
                             title="Categoria × estado do item (nº de anúncios)")

        _mostrar(
            c3,
            query_df(
                """SELECT i.nome_categoria AS categoria, i.estado, COUNT(*) AS qtd
                   FROM anuncio a JOIN item i ON i.id_item = a.id_item GROUP BY 1, 2"""
            ),
            heat,
        )
        _mostrar(
            c4,
            query_df(
                """SELECT t.nome_tag AS tag, COUNT(DISTINCT a.id_anuncio) AS anuncios
                   FROM item_tag t JOIN anuncio a ON a.id_item = t.id_item
                   GROUP BY 1 ORDER BY 2 DESC LIMIT 10"""
            ),
            lambda d: px.bar(d, x="anuncios", y="tag", orientation="h", title="Tags mais usadas"),
        )

        _mostrar(
            st,
            query_df(
                """SELECT i.nome_categoria AS categoria, COUNT(*) AS total,
                          COUNT(*) FILTER (WHERE a.status = 'Vendido') AS vendidos,
                          ROUND(100.0 * COUNT(*) FILTER (WHERE a.status = 'Vendido')
                                / COUNT(*), 1)::float AS taxa_conversao
                   FROM anuncio a JOIN item i ON i.id_item = a.id_item
                   GROUP BY 1 ORDER BY 4 DESC"""
            ),
            lambda d: px.bar(d, x="categoria", y="taxa_conversao", hover_data=["total", "vendidos"],
                             title="Taxa de conversão (anúncios vendidos, %) por categoria"),
        )

    # ---------------- Usuários ----------------
    with tab_usuarios:
        c1, c2 = st.columns(2)
        _mostrar(
            c1,
            query_df(
                """SELECT CASE WHEN idade < 20 THEN '16-19' WHEN idade < 30 THEN '20-29'
                               WHEN idade < 40 THEN '30-39' WHEN idade < 50 THEN '40-49'
                               ELSE '50+' END AS faixa, COUNT(*) AS usuarios
                   FROM (SELECT EXTRACT(YEAR FROM age(data_nascimento))::int AS idade
                         FROM usuario) s
                   GROUP BY 1 ORDER BY 1"""
            ),
            lambda d: px.bar(d, x="faixa", y="usuarios", title="Usuários por faixa etária"),
        )
        top = query_df(
            """SELECT u.nome, COUNT(t.id_transacao) AS vendas,
                      SUM(t.valor)::float AS faturamento,
                      MAX(n.nota_media) AS nota_media
               FROM usuario u
               JOIN anuncio a ON a.cpf_vendedor = u.cpf
               JOIN transacao t ON t.id_anuncio = a.id_anuncio AND t.status = 'Concluída'
               LEFT JOIN (SELECT cpf_avaliado, AVG(nota)::float AS nota_media
                          FROM avaliacao GROUP BY cpf_avaliado) n ON n.cpf_avaliado = u.cpf
               GROUP BY u.cpf, u.nome
               HAVING COUNT(t.id_transacao) >= 1
               ORDER BY faturamento DESC LIMIT 10"""
        )
        _mostrar(
            c2,
            top,
            lambda d: px.scatter(
                d.fillna({"nota_media": 0}), x="vendas", y="faturamento", size="faturamento",
                color="nota_media", hover_name="nome", range_color=[0, 5],
                title="Vendedores: vendas × faturamento (cor = nota média)",
            ),
        )

        def atividade(d):
            ordem = d.groupby("nome")["qtd"].sum().nlargest(10).index
            d = d[d["nome"].isin(ordem)]
            return px.bar(d, x="nome", y="qtd", color="acao",
                          title="Usuários mais ativos (top 10)")

        _mostrar(
            st,
            query_df(
                """SELECT u.nome, x.acao, COUNT(*) AS qtd FROM (
                       SELECT cpf_vendedor AS cpf, 'Anúncios' AS acao FROM anuncio
                       UNION ALL SELECT cpf_comentador, 'Comentários' FROM comentario
                       UNION ALL SELECT cpf_remetente, 'Mensagens' FROM mensagem
                       UNION ALL SELECT cpf_comprador, 'Compras' FROM transacao
                   ) x JOIN usuario u ON u.cpf = x.cpf
                   GROUP BY u.nome, x.acao"""
            ),
            atividade,
        )

    # ---------------- Operação ----------------
    with tab_op:
        funil = query_df(
            """SELECT COUNT(*) AS criadas,
                      COUNT(*) FILTER (WHERE p.status = 'Pago') AS pagas,
                      COUNT(*) FILTER (WHERE e.status IN ('Enviado', 'Recebido')) AS enviadas,
                      COUNT(*) FILTER (WHERE e.status = 'Recebido') AS recebidas,
                      COUNT(*) FILTER (WHERE t.status = 'Concluída') AS concluidas
               FROM transacao t
               JOIN pagamento p ON p.id_transacao = t.id_transacao
               JOIN entrega e ON e.id_transacao = t.id_transacao"""
        ).iloc[0]
        if int(funil["criadas"]) == 0:
            st.info("Ainda não há transações para analisar.")
        else:
            c1, c2 = st.columns(2)
            etapas = pd.DataFrame({"etapa": list(funil.index), "qtd": [int(v) for v in funil.values]})
            c1.plotly_chart(px.funnel(etapas, x="qtd", y="etapa", title="Funil das transações"),
                            width="stretch")
            _mostrar(
                c2,
                query_df(
                    "SELECT metodo, COUNT(*) AS qtd, SUM(valor)::float AS valor FROM pagamento GROUP BY 1"
                ),
                lambda d: px.pie(d, names="metodo", values="qtd", title="Métodos de pagamento"),
            )

            tempos = query_df(
                """SELECT AVG(EXTRACT(EPOCH FROM (p.data_hora_pagamento - t.data_hora)) / 3600)::float AS pag,
                          AVG(EXTRACT(EPOCH FROM (e.data_hora_envio - p.data_hora_pagamento)) / 3600)::float AS env,
                          AVG(EXTRACT(EPOCH FROM (e.data_recebimento - e.data_hora_envio)) / 3600)::float AS rec
                   FROM transacao t
                   JOIN pagamento p ON p.id_transacao = t.id_transacao
                   JOIN entrega e ON e.id_transacao = t.id_transacao"""
            ).iloc[0]
            t1, t2, t3 = st.columns(3)
            fmt = lambda v: "—" if pd.isna(v) else f"{v:.1f} h"
            t1.metric("Criação → pagamento", fmt(tempos["pag"]))
            t2.metric("Pagamento → envio", fmt(tempos["env"]))
            t3.metric("Envio → recebimento", fmt(tempos["rec"]))

        _mostrar(
            st,
            query_df(
                """SELECT i.nome_categoria AS categoria, s.status, COUNT(*) AS chamados
                   FROM suporte s
                   JOIN anuncio a ON a.id_anuncio = s.id_anuncio
                   JOIN item i ON i.id_item = a.id_item
                   GROUP BY 1, 2"""
            ),
            lambda d: px.bar(d, x="categoria", y="chamados", color="status",
                             title="Chamados de suporte por categoria e status"),
        )
