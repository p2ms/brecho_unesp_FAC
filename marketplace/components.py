"""Componentes de interface reutilizados por mais de uma página."""
import pandas as pd
import streamlit as st

from .auth import current_user
from .erros import ErroAplicacao
from .services import interacoes


def chat(id_anuncio, meu_cpf, outro_cpf, key):
    msgs = interacoes.listar_mensagens(id_anuncio, meu_cpf, outro_cpf)
    if msgs.empty:
        st.caption("Nenhuma mensagem ainda.")
    for _, m in msgs.iterrows():
        papel = "user" if m["cpf_remetente"].strip() == meu_cpf else "assistant"
        with st.chat_message(papel):
            st.caption(f"{m['nome']} · {m['data_hora']:%d/%m/%Y %H:%M}")
            st.write(m["texto"])

    with st.form(f"form_chat_{key}", clear_on_submit=True):
        texto = st.text_area("Nova mensagem", height=80)
        if st.form_submit_button("Enviar") and texto.strip():
            try:
                interacoes.enviar_mensagem(meu_cpf, outro_cpf, id_anuncio, texto)
                st.rerun()
            except ErroAplicacao as e:
                st.error(str(e))


def comentarios(id_anuncio):
    df = interacoes.listar_comentarios(id_anuncio)
    user = current_user()
    if user:
        with st.form(f"form_coment_{id_anuncio}", clear_on_submit=True):
            texto = st.text_area("Comentar", height=80)
            if st.form_submit_button("Publicar comentário") and texto.strip():
                try:
                    interacoes.publicar_comentario(user["cpf"], id_anuncio, texto)
                    st.rerun()
                except ErroAplicacao as e:
                    st.error(str(e))
    else:
        st.caption("Entre na sua conta para comentar.")

    if df.empty:
        st.caption("Sem comentários ainda.")
    for _, c in df.iterrows():
        with st.container(border=True):
            st.caption(f"{c['nome']} · {c['data_hora']:%d/%m/%Y %H:%M}")
            st.write(c["texto"])


def card_preco(a):
    if a["tipo"] == "Empréstimo":
        prazo = int(a["prazo"]) if pd.notna(a["prazo"]) else "?"
        return f"R$ {a['preco']:.2f} · empréstimo por {prazo} dia(s)"
    return f"R$ {a['preco']:.2f}"
