"""Página Loja: vitrine de anúncios e detalhe com compra, comentários e chat."""
import streamlit as st

from ..auth import current_user
from ..components import card_preco, chat, comentarios, eh_link
from ..config import ESTADOS, METODOS_ENTREGA, METODOS_PAGAMENTO, TIPOS
from ..erros import ErroAplicacao
from ..services import anuncios, transacoes


def pagina_loja():
    sel = st.session_state.get("anuncio_sel")
    if sel:
        return detalhe_anuncio(sel)

    st.header(":material/storefront: Anúncios disponíveis")
    df = anuncios.buscar_anuncios()
    if df.empty:
        st.info("Nenhum anúncio disponível ainda.")
        return

    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    busca = c1.text_input(":material/search: Buscar", placeholder="título, item, marca ou tag...")
    categoria = c2.selectbox("Categoria", ["Todas"] + sorted(df["nome_categoria"].unique()))
    tipo = c3.selectbox("Tipo", ["Todos"] + TIPOS)
    estado = c4.selectbox("Estado", ["Todos"] + ESTADOS)

    pmax = float(df["preco"].max())
    if pmax > 0:
        faixa = st.slider("Faixa de preço (R$)", 0.0, pmax, (0.0, pmax))
        df = df[df["preco"].between(*faixa)]

    if busca:
        campos = df[["titulo", "item", "marca", "tags"]].fillna("").agg(" ".join, axis=1)
        df = df[campos.str.contains(busca, case=False, na=False)]
    if categoria != "Todas":
        df = df[df["nome_categoria"] == categoria]
    if tipo != "Todos":
        df = df[df["tipo"] == tipo]
    if estado != "Todos":
        df = df[df["estado"] == estado]

    st.caption(f"{len(df)} anúncio(s)")
    cols = st.columns(3)
    for i, (_, a) in enumerate(df.iterrows()):
        with cols[i % 3].container(border=True, key=f"card_anuncio_{a['id_anuncio']}"):
            if eh_link(a["foto"]):
                st.image(a["foto"], width="stretch")
            st.subheader(a["titulo"])
            st.caption(f"{a['tipo']} · {a['estado']} · {a['nome_categoria']}")
            st.markdown(f"**{card_preco(a)}**")
            st.caption(f"Vendedor: {a['vendedor']}")
            if a["tags"]:
                st.caption(":material/label: " + a["tags"])
            if st.button("Ver detalhes", key=f"ver_{a['id_anuncio']}", width="stretch"):
                st.session_state["anuncio_sel"] = int(a["id_anuncio"])
                st.rerun()


def detalhe_anuncio(id_anuncio):
    if st.button(":material/arrow_back: Voltar"):
        st.session_state["anuncio_sel"] = None
        st.rerun()

    df = anuncios.buscar_anuncios(apenas_disponiveis=False, id_anuncio=id_anuncio)
    if df.empty:
        st.error("Anúncio não encontrado.")
        return
    a = df.iloc[0]
    user = current_user()

    col_fotos, col_info = st.columns([1, 1])
    fotos = [f for f in anuncios.listar_fotos(id_anuncio)["url_foto"] if eh_link(f)]
    with col_fotos:
        if not fotos:
            st.info("Sem fotos.")
        else:
            st.image(fotos, width="stretch")

    with col_info:
        st.title(a["titulo"])
        st.markdown(f"## {card_preco(a)}")
        st.write(f"**Status:** {a['status']} · **Tipo:** {a['tipo']}")
        st.write(f"**Item:** {a['item']} ({a['marca'] or 'sem marca'}) · **Estado:** {a['estado']}")
        st.write(f"**Categoria:** {a['nome_categoria']}")
        if a["tags"]:
            st.write(":material/label: " + a["tags"])
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
                if st.form_submit_button(rotulo, width="stretch"):
                    try:
                        id_t = transacoes.criar_transacao(
                            user["cpf"], id_anuncio, metodo_pag, metodo_ent
                        )
                        if id_t:
                            st.success(f"Transação #{id_t} criada! Acompanhe em 'Minhas compras'.")
                        else:
                            st.error("Este anúncio acabou de ser reservado por outra pessoa.")
                    except ErroAplicacao as e:
                        st.error(str(e))

    tab_com, tab_msg = st.tabs([":material/chat: Comentários", ":material/mail: Mensagem ao vendedor"])
    with tab_com:
        comentarios(id_anuncio)
    with tab_msg:
        if user is None:
            st.caption("Entre na sua conta para enviar mensagens.")
        elif user["cpf"] == a["cpf_vendedor"]:
            st.caption("Responda mensagens na página 'Mensagens'.")
        else:
            chat(id_anuncio, user["cpf"], a["cpf_vendedor"], key=f"det_{id_anuncio}")
