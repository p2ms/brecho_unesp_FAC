"""Páginas Minhas compras e Minhas vendas."""
import psycopg2
import streamlit as st

from ..auth import require_login
from ..db import db_error, execute, query_df
from ..services import confirmar_recebimento, marcar_enviado, pagar


def listar_transacoes(papel):
    """papel = 'comprador' ou 'vendedor'"""
    user = require_login()
    filtro = "t.cpf_comprador" if papel == "comprador" else "a.cpf_vendedor"
    outro = (
        "(SELECT nome FROM usuario WHERE cpf = a.cpf_vendedor)"
        if papel == "comprador"
        else "(SELECT nome FROM usuario WHERE cpf = t.cpf_comprador)"
    )
    df = query_df(
        f"""SELECT t.id_transacao, t.data_hora, t.valor, t.status AS status_transacao,
                   a.id_anuncio, a.titulo, a.tipo, a.cpf_vendedor, {outro} AS outra_parte,
                   p.status AS pagamento, p.metodo AS metodo_pagamento,
                   e.status AS entrega, e.metodo AS metodo_entrega
            FROM transacao t
            JOIN anuncio a ON a.id_anuncio = t.id_anuncio
            JOIN pagamento p ON p.id_transacao = t.id_transacao
            JOIN entrega e ON e.id_transacao = t.id_transacao
            WHERE {filtro} = %s ORDER BY t.data_hora DESC""",
        (user["cpf"],),
    )
    if df.empty:
        st.info("Nada por aqui ainda.")
        return

    for _, t in df.iterrows():
        id_t = int(t["id_transacao"])
        with st.container(border=True):
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
                        "💳 Pagar", key=f"pagar_{id_t}", width="stretch"
                    ):
                        pagar(id_t)
                        st.rerun()
                    if t["entrega"] == "Enviado" and b2.button(
                        "📦 Confirmar recebimento", key=f"rec_{id_t}", width="stretch"
                    ):
                        confirmar_recebimento(id_t)
                        st.rerun()

                    if t["status_transacao"] == "Concluída":
                        with st.expander("⭐ Avaliar vendedor"):
                            nota = st.slider("Nota", 0, 5, 5, key=f"nota_{id_t}")
                            if st.button("Enviar avaliação", key=f"aval_{id_t}"):
                                execute(
                                    """INSERT INTO avaliacao (cpf_avaliador, cpf_avaliado, nota)
                                       VALUES (%s, %s, %s)""",
                                    (user["cpf"], t["cpf_vendedor"].strip(), nota),
                                )
                                st.success("Avaliação enviada!")
                    with st.expander("🛟 Abrir chamado de suporte"):
                        desc = st.text_area("Descreva o problema", key=f"sup_txt_{id_t}")
                        if st.button("Abrir chamado", key=f"sup_{id_t}") and desc.strip():
                            execute(
                                """INSERT INTO suporte (id_anuncio, cpf_cliente, descricao)
                                   VALUES (%s, %s, %s)""",
                                (int(t["id_anuncio"]), user["cpf"], desc.strip()),
                            )
                            st.success("Chamado aberto!")
                else:
                    if t["entrega"] == "Pendente" and st.button(
                        "🚚 Marcar como enviado", key=f"env_{id_t}"
                    ):
                        marcar_enviado(id_t)
                        st.rerun()
            except psycopg2.Error as e:
                db_error(e)


def pagina_compras():
    user = require_login()
    st.header("📦 Minhas compras")
    listar_transacoes("comprador")

    st.subheader("Meus chamados de suporte")
    sup = query_df(
        """SELECT s.id_suporte AS id, a.titulo AS anuncio, s.descricao, s.status, s.data_hora
           FROM suporte s JOIN anuncio a ON a.id_anuncio = s.id_anuncio
           WHERE s.cpf_cliente = %s ORDER BY s.data_hora DESC""",
        (user["cpf"],),
    )
    st.dataframe(sup, width="stretch", hide_index=True)


def pagina_vendas():
    require_login()
    st.header("💼 Minhas vendas")
    listar_transacoes("vendedor")
