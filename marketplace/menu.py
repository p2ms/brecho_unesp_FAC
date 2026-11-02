"""Menu lateral: nome do site, páginas, sacola, conta e busca."""
import streamlit as st

from .auth import current_user
from .estilo import sol_html
from .navegacao import pagina
from .services import transacoes

_PARAMETROS = {"loja": ("q", "categoria"), "anuncio": ("id",), "conta": ("aba",)}


def _linha(rotulo, icone, nome, atual, parametros=None, chave=None):
    with st.container(key="menu_ativo" if nome == atual and not chave else f"menu_{chave or nome}"):
        st.page_link(
            pagina(nome), label=rotulo, icon=f":material/{icone}:", query_params=parametros, width="stretch"
        )


def _busca(atual):
    """Mantém o campo igual ao ?q= da Loja; ao digitar, abre a Loja com o termo."""
    if atual == "loja" or "busca_menu" not in st.session_state:
        q = st.query_params.get("q", "")
        if st.session_state.get("_busca_ultima") != q:
            st.session_state["busca_menu"] = q
            st.session_state["_busca_ultima"] = q

    with st.container(key="menu_busca"):
        termo = st.text_input(":material/search: Busca", key="busca_menu", placeholder="título, item, marca ou tag").strip()
    if termo != st.session_state["_busca_ultima"]:
        st.session_state["_busca_ultima"] = termo
        if atual != "loja":
            st.switch_page(pagina("loja"), query_params={"q": termo} if termo else None)
        # Na mesma página, um link não atualiza o endereço: é preciso escrever nele
        if termo:
            st.query_params["q"] = termo
        else:
            st.query_params.pop("q", None)
        st.rerun()


def _sincronizar_endereco(pagina_atual):
    """Um link para a própria página não muda o endereço, e voltar pode trazer parâmetros de outra página."""
    aceitos = _PARAMETROS.get(pagina_atual, ())
    st.query_params.from_dict({k: v for k, v in st.query_params.to_dict().items() if k in aceitos})


def menu(atual):
    _sincronizar_endereco(atual)
    user = current_user()
    with st.sidebar:
        with st.container(key="menu_ativo" if atual in ("loja", "anuncio") else "menu_marca"):
            st.page_link(pagina("loja"), label="Brechó da Unesp", width="stretch")
        _linha("Anunciar", "sell", "anunciar", atual)
        _linha("Minha loja", "store", "minha_loja", atual)
        _linha("Mensagens", "mail", "mensagens", atual)
        _linha("Painel", "bar_chart", "painel", atual)
        pendentes = f" ({transacoes.contar_pendentes(user['cpf'])})" if user else ""
        _linha(f"Sacola{pendentes}", "shopping_bag", "conta", atual, {"aba": "compras"}, chave="sacola")
        _linha("Minha conta", "person", "conta", atual)
        _busca(atual)
        with st.container(key="menu_sol"):
            st.html(sol_html())
