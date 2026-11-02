"""Páginas Minhas compras e Minhas vendas."""
import streamlit as st

from ..auth import require_login
from ..erros import ErroAplicacao
from ..services import anuncios, transacoes


def _mostrar_transacoes(papel):
    """papel = 'comprador' ou 'vendedor'"""
    user = require_login()
    df = transacoes.listar_transacoes(user["cpf"], papel)
    if df.empty:
        st.info("Nada por aqui ainda.")
        return

    for _, t in df.iterrows():
        id_t = int(t["id_transacao"])
        with st.container(border=True, key=f"card_transacao_{id_t}"):
            c1, c2 = st.columns([3, 2])
            c1.subheader(f"#{id_t} · {t['titulo']}")
            c1.caption(
                f"{'Vendedor' if papel == 'comprador' else 'Comprador'}: {t['outra_parte']} · "
                f"{t['data_hora']:%d/%m/%Y %H:%M} · {t['tipo']}"
            )
            c2.metric("Valor", f"R$ {float(t['valor']):.2f}")
            st.write(
                f"**Transação:** {t['status_transacao']} · "
                f"**Pagamento:** {t['pagamento']} ({t['metodo_pagamento']}) · "
                f"**Entrega:** {t['entrega']} ({t['metodo_entrega']})"
            )

            try:
                if papel == "comprador":
                    b1, b2 = st.columns(2)
                    if t["pagamento"] == "Pendente" and b1.button(
                        "Pagar", key=f"pagar_{id_t}", type="primary", width="stretch"
                    ):
                        transacoes.pagar(id_t, user["cpf"])
                        st.rerun()
                    if t["entrega"] == "Enviado" and b2.button(
                        "Confirmar recebimento", key=f"rec_{id_t}", type="primary", width="stretch"
                    ):
                        transacoes.confirmar_recebimento(id_t, user["cpf"])
                        st.rerun()

                    if t["status_transacao"] == "Concluída":
                        with st.expander("Avaliar vendedor"):
                            nota = st.slider("Nota", 0, 5, 5, key=f"nota_{id_t}")
                            if st.button("Enviar avaliação", key=f"aval_{id_t}", type="primary"):
                                transacoes.avaliar_vendedor(id_t, user["cpf"], nota)
                                st.success("Avaliação enviada!")
                    with st.expander("Abrir chamado de suporte"):
                        desc = st.text_area("Descreva o problema", key=f"sup_txt_{id_t}")
                        if st.button("Abrir chamado", key=f"sup_{id_t}") and desc.strip():
                            transacoes.abrir_chamado(id_t, user["cpf"], desc)
                            st.success("Chamado aberto!")
                else:
                    if t["entrega"] == "Pendente" and st.button(
                        "Marcar como enviado", key=f"env_{id_t}", type="primary"
                    ):
                        transacoes.marcar_enviado(id_t, user["cpf"])
                        st.rerun()
            except ErroAplicacao as e:
                st.error(str(e))


def pagina_compras():
    user = require_login()
    _mostrar_transacoes("comprador")

    sup = transacoes.listar_chamados(user["cpf"])
    if not sup.empty:
        st.subheader("Meus chamados de suporte")
        st.dataframe(sup, width="stretch", hide_index=True)


def pagina_vendas():
    user = require_login()
    _mostrar_transacoes("vendedor")

    meus = anuncios.listar_do_vendedor(user["cpf"])
    if not meus.empty and meus["bloqueado"].any():
        st.subheader("Anúncios que não podem mais ser editados")
        colunas = ["id", "titulo", "tipo", "preco", "status", "publicado_em"]
        st.dataframe(meus.loc[meus["bloqueado"], colunas], width="stretch", hide_index=True)
