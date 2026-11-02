"""Página Dashboard: análises visuais e estatísticas."""
import pandas as pd
import plotly.express as px
import streamlit as st

from ..services import analises


def _mostrar(col, df, fig_fn):
    if df.empty:
        col.caption("Sem dados para este gráfico.")
    else:
        col.plotly_chart(fig_fn(df), width="stretch")


def pagina_dashboard():
    st.header(":material/bar_chart: Dashboard analítico")
    tab_geral, tab_mercado, tab_usuarios, tab_op = st.tabs(
        ["Visão geral", "Mercado", "Usuários", "Operação"]
    )

    # ---------------- Visão geral ----------------
    with tab_geral:
        kpi = analises.indicadores_gerais()
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Usuários", int(kpi["usuarios"]))
        k2.metric("Anúncios disponíveis", int(kpi["disponiveis"]))
        k3.metric("Transações concluídas", int(kpi["concluidas"]))
        k4.metric("Volume transacionado", f"R$ {float(kpi['volume']):,.2f}")

        c1, c2 = st.columns(2)
        _mostrar(
            c1,
            analises.anuncios_por_categoria(),
            lambda d: px.bar(d, x="categoria", y="anuncios", title="Anúncios por categoria"),
        )
        _mostrar(
            c2,
            analises.anuncios_por_status(),
            lambda d: px.pie(d, names="status", values="qtd", title="Anúncios por status"),
        )

        _mostrar(
            st,
            analises.publicacoes_por_semana(),
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
            analises.preco_por_categoria_raiz(),
            lambda d: px.bar(
                d, x="categoria_raiz", y="preco_medio", hover_data=["anuncios"],
                title="Preço médio por categoria raiz (inclui subcategorias)",
            ),
        )
        _mostrar(
            c2,
            analises.precos_por_estado(),
            lambda d: px.box(d, x="estado", y="preco", points="all",
                             title="Distribuição de preços por estado do item"),
        )

        c3, c4 = st.columns(2)

        def heat(d):
            pivot = d.pivot_table(index="categoria", columns="estado", values="qtd", fill_value=0)
            return px.imshow(pivot, text_auto=True, aspect="auto",
                             title="Categoria × estado do item (nº de anúncios)")

        _mostrar(c3, analises.categoria_por_estado(), heat)
        _mostrar(
            c4,
            analises.tags_mais_usadas(),
            lambda d: px.bar(d, x="anuncios", y="tag", orientation="h", title="Tags mais usadas"),
        )

        _mostrar(
            st,
            analises.conversao_por_categoria(),
            lambda d: px.bar(d, x="categoria", y="taxa_conversao", hover_data=["total", "vendidos"],
                             title="Taxa de conversão (anúncios vendidos, %) por categoria"),
        )

    # ---------------- Usuários ----------------
    with tab_usuarios:
        c1, c2 = st.columns(2)
        _mostrar(
            c1,
            analises.usuarios_por_faixa_etaria(),
            lambda d: px.bar(d, x="faixa", y="usuarios", title="Usuários por faixa etária"),
        )
        _mostrar(
            c2,
            analises.melhores_vendedores(),
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

        _mostrar(st, analises.atividade_usuarios(), atividade)

    # ---------------- Operação ----------------
    with tab_op:
        funil = analises.funil_transacoes()
        if int(funil["criadas"]) == 0:
            st.info("Ainda não há transações para analisar.")
        else:
            c1, c2 = st.columns(2)
            etapas = pd.DataFrame({"etapa": list(funil.index), "qtd": [int(v) for v in funil.values]})
            c1.plotly_chart(px.funnel(etapas, x="qtd", y="etapa", title="Funil das transações"),
                            width="stretch")
            _mostrar(
                c2,
                analises.metodos_pagamento(),
                lambda d: px.pie(d, names="metodo", values="qtd", title="Métodos de pagamento"),
            )

            tempos = analises.tempos_transacao()
            t1, t2, t3 = st.columns(3)
            fmt = lambda v: "—" if pd.isna(v) else f"{v:.1f} h"
            t1.metric("Criação → pagamento", fmt(tempos["pag"]))
            t2.metric("Pagamento → envio", fmt(tempos["env"]))
            t3.metric("Envio → recebimento", fmt(tempos["rec"]))

        _mostrar(
            st,
            analises.chamados_por_categoria(),
            lambda d: px.bar(d, x="categoria", y="chamados", color="status",
                             title="Chamados de suporte por categoria e status"),
        )
