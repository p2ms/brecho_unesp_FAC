"""Página Minha loja: anúncios sem transação, que o vendedor ainda pode editar ou apagar."""
import pandas as pd
import streamlit as st

from ..auth import require_login
from ..components import eh_link
from ..config import ESTADOS
from ..erros import ErroAplicacao
from ..services import anuncios


@st.dialog("Editar anúncio", width="large")
def _editar(cpf, id_anuncio):
    df = anuncios.buscar_anuncios(apenas_disponiveis=False, id_anuncio=id_anuncio)
    if df.empty:
        st.error("Anúncio não encontrado.")
        return
    a = df.iloc[0]
    cats = list(anuncios.listar_categorias()["nome_categoria"])
    fotos = list(anuncios.listar_fotos(id_anuncio)["url_foto"])

    with st.form(f"editar_{id_anuncio}"):
        titulo = st.text_input("Título", value=a["titulo"])
        descricao = st.text_area("Descrição do anúncio", value=a["descricao_anuncio"] or "")
        c1, c2 = st.columns(2)
        preco = c1.number_input("Preço (R$)", min_value=0.0, step=1.0, value=float(a["preco"]))
        prazo = None
        if a["tipo"] == "Empréstimo":
            atual = int(a["prazo"]) if pd.notna(a["prazo"]) else 1
            prazo = c2.number_input("Prazo do empréstimo (dias)", min_value=1, step=1, value=atual)

        item = st.text_input("Nome do item", value=a["item"])
        c3, c4 = st.columns(2)
        marca = c3.text_input("Marca", value=a["marca"] or "")
        estado = c4.selectbox("Estado", ESTADOS, index=ESTADOS.index(a["estado"]))
        categoria = st.selectbox("Categoria", cats, index=cats.index(a["nome_categoria"]))
        descricao_item = st.text_area("Descrição do item", value=a["descricao_item"] or "")
        tags = st.text_input("Tags (separadas por vírgula)", value=a["tags"] or "")

        removidas = []
        if fotos:
            st.markdown("**Fotos atuais**")
            colunas = st.columns(len(fotos))
            for i, (coluna, foto) in enumerate(zip(colunas, fotos)):
                if eh_link(foto):
                    coluna.image(foto, width="stretch")
                else:
                    coluna.caption("Arquivo indisponível")
                if coluna.checkbox("Remover", key=f"remover_{id_anuncio}_{i}"):
                    removidas.append(foto)
        novas = st.file_uploader(
            "Adicionar fotos (até 5 no total, em JPG, PNG ou WebP, com até 5 MB cada)",
            type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True,
        )

        if st.form_submit_button("Salvar", type="primary", width="stretch"):
            dados = {
                "titulo": titulo, "descricao": descricao, "preco": preco, "prazo": prazo and int(prazo),
                "item": item, "marca": marca, "estado": estado, "categoria": categoria,
                "descricao_item": descricao_item, "tags": tags.split(","),
                "fotos_removidas": removidas, "fotos_novas": [f.getvalue() for f in novas],
            }
            try:
                anuncios.editar_anuncio(cpf, id_anuncio, dados)
                st.session_state["aviso_anuncios"] = "Anúncio atualizado."
                st.rerun()
            except ErroAplicacao as e:
                st.error(str(e))


@st.dialog("Apagar anúncio")
def _apagar(cpf, id_anuncio, titulo):
    st.write(f"Apagar **{titulo}**? As fotos, os comentários e as mensagens dele também serão apagados.")
    c1, c2 = st.columns(2)
    if c1.button("Apagar", type="primary", width="stretch"):
        try:
            anuncios.apagar_anuncio(cpf, id_anuncio)
            st.session_state["aviso_anuncios"] = "Anúncio apagado."
            st.rerun()
        except ErroAplicacao as e:
            st.error(str(e))
    if c2.button("Cancelar", width="stretch"):
        st.rerun()


def pagina_minha_loja():
    user = require_login()
    st.header(":material/store: Minha loja")
    aviso = st.session_state.pop("aviso_anuncios", None)
    if aviso:
        st.success(aviso)

    meus = anuncios.listar_do_vendedor(user["cpf"])
    if not meus.empty:
        meus = meus[~meus["bloqueado"]]
    if meus.empty:
        st.info("Nenhum anúncio para editar. Os que já têm transação ficam em 'Minhas vendas'.")
        return

    for _, a in meus.iterrows():
        id_anuncio = int(a["id"])
        with st.container(border=True, key=f"card_meu_anuncio_{id_anuncio}"):
            c1, c2, c3 = st.columns([6, 1, 1], vertical_alignment="center")
            c1.markdown(f"**{a['titulo']}**")
            c1.caption(f"{a['tipo']} · R$ {float(a['preco']):.2f} · {a['status']}")
            if c2.button("Editar", key=f"editar_{id_anuncio}", width="stretch"):
                _editar(user["cpf"], id_anuncio)
            if c3.button("Apagar", key=f"apagar_{id_anuncio}", width="stretch"):
                _apagar(user["cpf"], id_anuncio, a["titulo"])
