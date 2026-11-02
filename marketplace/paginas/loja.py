"""Página Loja: capa, vitrine com busca combinada e detalhe com compra, comentários e chat."""
import streamlit as st

from ..auth import current_user
from ..components import card_preco, chat, comentarios, eh_link
from ..config import ESTADOS, METODOS_ENTREGA, METODOS_PAGAMENTO, TIPOS
from ..erros import ErroAplicacao
from ..estilo import VINHO, sol_html
from ..navegacao import pagina, trilha
from ..services import anuncios, transacoes

POR_PAGINA = 9


def _capa():
    st.html(
        f'<div class="capa">{sol_html(460, VINHO)}<h1>brechó da unesp</h1>'
        "<p>Compre, venda e empreste.</p></div>"
    )


def _faixa():
    item = f"<span>{sol_html(22)}LOJA</span>"
    st.html(f'<div class="faixa">{item * 8}</div>')


def _filtros(texto):
    """Monta os filtros e devolve os argumentos de anuncios.busca_avancada."""
    tipo = st.segmented_control(
        "Tipo", ["Todos"] + TIPOS, default="Todos", required=True, label_visibility="collapsed"
    )
    categorias = [""] + list(anuncios.listar_categorias()["nome_categoria"])
    pedida = st.query_params.get("categoria")
    pmax = anuncios.preco_maximo() or 100.0

    with st.expander("Mais filtros", expanded=pedida in categorias):
        c1, c2, c3 = st.columns(3)
        categoria = c1.selectbox(
            "Categoria (inclui subcategorias)", categorias,
            index=categorias.index(pedida) if pedida in categorias else 0,
            format_func=lambda c: c or "Todas",
        )
        tags = c2.multiselect(
            "Tags (o item precisa ter todas)", list(anuncios.listar_tags()["nome_tag"])
        )
        estados = c3.multiselect("Estado do item", ESTADOS)

        c4, c5 = st.columns(2)
        faixa = c4.slider("Faixa de preço (R$)", 0.0, pmax, (0.0, pmax))
        nota_min = c5.slider("Nota mínima do vendedor", 0.0, 5.0, 0.0, 0.5)

        c6, c7 = st.columns(2)
        dias = c6.number_input("Publicados nos últimos N dias (0 = qualquer)", 0, 3650, 0)
        ordem = c7.selectbox("Ordenar por", list(anuncios.ORDENS_BUSCA))

    return {
        "texto": texto, "categoria": categoria, "tags": tags, "estados": estados, "tipo": tipo,
        "nota_min": nota_min, "faixa": faixa, "dias": dias, "ordem": ordem,
    }


def _mostrar_mais():
    st.session_state["_loja_limite"] += POR_PAGINA


def _card(a):
    with st.container(border=True, key=f"card_anuncio_{a['id']}"):
        st.html(f'<div class="card-tipo">{a["tipo"]}</div>')
        if eh_link(a["foto"]):
            st.image(a["foto"], width="stretch")
        else:
            st.html(f'<div class="sem-foto">{sol_html(96)}</div>')
        st.subheader(a["titulo"])
        st.caption(f"{a['estado']} · {a['categoria']}")
        st.caption(a["vendedor"])
        st.markdown(f"**{card_preco(a)}**")
        st.page_link(
            pagina("anuncio"), label="Ver detalhes", width="stretch",
            query_params={"id": int(a["id"])},
        )


def pagina_loja():
    busca = st.query_params.get("q", "").strip()
    trilha(("LOJA", "loja"), f"BUSCA: {busca}" if busca else "TODOS OS ANÚNCIOS")
    if not busca:
        _capa()
        _faixa()

    filtros = _filtros(busca)
    df, sql = anuncios.busca_avancada(**filtros)

    # Com outros filtros, a lista volta a mostrar só a primeira parte
    if st.session_state.get("_loja_filtros") != repr(filtros):
        st.session_state["_loja_filtros"] = repr(filtros)
        st.session_state["_loja_limite"] = POR_PAGINA
    limite = st.session_state["_loja_limite"]

    if df.empty:
        st.info("Nenhum anúncio encontrado.")
    else:
        st.caption(
            f"{len(df)} anúncio(s) · preço médio R$ {df['preco'].mean():.2f} · "
            f"mediana R$ {df['preco'].median():.2f}"
        )
        cols = st.columns(3)
        for i, (_, a) in enumerate(df.head(limite).iterrows()):
            with cols[i % 3]:
                _card(a)
        if len(df) > limite:
            st.button("Ver mais anúncios", on_click=_mostrar_mais, width="stretch")

    with st.expander("Ver SQL gerado"):
        st.code(sql, language="sql")


def pagina_anuncio():
    id_url = st.query_params.get("id", "")
    id_anuncio = int(id_url) if id_url.isdigit() else None
    df = anuncios.buscar_anuncios(apenas_disponiveis=False, id_anuncio=id_anuncio) if id_anuncio else None
    if df is None or df.empty:
        trilha(("LOJA", "loja"), "ANÚNCIO NÃO ENCONTRADO")
        st.error("Anúncio não encontrado.")
        return
    a = df.iloc[0]
    trilha(
        ("LOJA", "loja"),
        (a["nome_categoria"].upper(), "loja", {"categoria": a["nome_categoria"]}),
        a["titulo"].upper(),
    )
    user = current_user()

    col_fotos, col_info = st.columns([1, 1])
    fotos = [f for f in anuncios.listar_fotos(id_anuncio)["url_foto"] if eh_link(f)]
    with col_fotos:
        if not fotos:
            st.html(f'<div class="sem-foto grande">{sol_html(300, VINHO)}<span>SEM FOTOS</span></div>')
        else:
            st.image(fotos, width="stretch")

    with col_info:
        st.title(a["titulo"])
        st.markdown(f"## {card_preco(a)}")
        st.write(f"**Status:** {a['status']} · **Tipo:** {a['tipo']}")
        st.write(f"**Item:** {a['item']} ({a['marca'] or 'sem marca'}) · **Estado:** {a['estado']}")
        st.write(f"**Categoria:** {a['nome_categoria']}")
        if a["tags"]:
            st.write(f"**Tags:** {a['tags']}")
        st.write(f"**Vendedor:** {a['vendedor']}")
        if a["descricao_anuncio"]:
            st.write(a["descricao_anuncio"])
        if a["descricao_item"]:
            st.caption(a["descricao_item"])

        st.divider()
        if a["status"] != "Disponível":
            st.warning(f"Este anúncio está {a['status'].lower()}.")
        elif user is None:
            st.info("Entre na sua conta para comprar.")
        elif user["cpf"] == a["cpf_vendedor"]:
            st.info("Este é o seu anúncio. Para editar ou apagar, vá em 'Minha loja'.")
        else:
            rotulo = "Solicitar empréstimo" if a["tipo"] == "Empréstimo" else "Comprar"
            with st.form(f"form_compra_{id_anuncio}"):
                metodo_pag = st.selectbox("Forma de pagamento", METODOS_PAGAMENTO)
                metodo_ent = st.selectbox("Forma de entrega", METODOS_ENTREGA)
                if st.form_submit_button(rotulo, type="primary", width="stretch"):
                    try:
                        id_t = transacoes.criar_transacao(
                            user["cpf"], id_anuncio, metodo_pag, metodo_ent
                        )
                        if id_t:
                            st.success(f"Transação #{id_t} criada! Acompanhe em 'Minha conta'.")
                        else:
                            st.error("Este anúncio acabou de ser reservado por outra pessoa.")
                    except ErroAplicacao as e:
                        st.error(str(e))

    tab_com, tab_msg = st.tabs(["Comentários", "Mensagem ao vendedor"])
    with tab_com:
        comentarios(id_anuncio)
    with tab_msg:
        if user is None:
            st.caption("Entre na sua conta para enviar mensagens.")
        elif user["cpf"] == a["cpf_vendedor"]:
            st.caption("Responda mensagens na página 'Mensagens'.")
        else:
            chat(id_anuncio, user["cpf"], a["cpf_vendedor"], key=f"det_{id_anuncio}")
