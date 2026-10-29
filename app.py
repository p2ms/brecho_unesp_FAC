import os
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
from dotenv import load_dotenv

# ---------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

st.set_page_config(page_title="Marketplace", page_icon="🔁", layout="wide")

if not DATABASE_URL:
    st.error("Defina DATABASE_URL no arquivo .env")
    st.stop()

ESTADOS = ["Novo", "Quase Novo", "Usado", "Razoável", "Com avarias"]
TIPOS = ["Venda", "Empréstimo"]
METODOS_PAGAMENTO = ["Pix", "Boleto", "Crédito", "Débito"]
METODOS_ENTREGA = ["Retirada em mãos", "Correios", "Transportadora"]


# ---------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------
def get_conn():
    # Uma conexão por operação: o Neon derruba conexões ociosas.
    return psycopg2.connect(DATABASE_URL)


def query_df(sql, params=None):
    """SELECT -> DataFrame"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [c[0] for c in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=cols)
    finally:
        conn.close()


def execute(sql, params=None):
    """INSERT/UPDATE/DELETE com commit automático."""
    conn = get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, params)
    finally:
        conn.close()


def run_tx(fn):
    """Executa fn(cur) em uma única transação (commit/rollback automáticos)."""
    conn = get_conn()
    try:
        with conn, conn.cursor() as cur:
            return fn(cur)
    finally:
        conn.close()


def db_error(e):
    msg = getattr(getattr(e, "diag", None), "message_primary", None) or str(e)
    st.error(f"Erro no banco de dados: {msg}")


def current_user():
    return st.session_state.get("user")


def require_login():
    if current_user() is None:
        st.warning("Entre na sua conta (menu lateral) para acessar esta página.")
        st.stop()
    return current_user()


# ---------------------------------------------------------------
# Consultas / operações de negócio
# ---------------------------------------------------------------
def buscar_anuncios(apenas_disponiveis=True, id_anuncio=None):
    sql = """
        SELECT a.id_anuncio, a.titulo, a.descricao AS descricao_anuncio, a.preco,
               a.tipo, a.status, a.data_hora_publicacao, a.cpf_vendedor,
               u.nome AS vendedor, i.id_item, i.nome AS item, i.marca, i.estado,
               i.descricao AS descricao_item, i.nome_categoria, e.prazo,
               (SELECT url_foto FROM foto_anuncio f
                 WHERE f.id_anuncio = a.id_anuncio ORDER BY f.id_foto LIMIT 1) AS foto,
               (SELECT string_agg(t.nome_tag, ', ') FROM item_tag t
                 WHERE t.id_item = i.id_item) AS tags
        FROM anuncio a
        JOIN usuario u ON u.cpf = a.cpf_vendedor
        JOIN item i ON i.id_item = a.id_item
        LEFT JOIN emprestimo e ON e.id_anuncio = a.id_anuncio
        WHERE 1 = 1
    """
    params = []
    if apenas_disponiveis:
        sql += " AND a.status = 'Disponível'"
    if id_anuncio is not None:
        sql += " AND a.id_anuncio = %s"
        params.append(id_anuncio)
    sql += " ORDER BY a.data_hora_publicacao DESC"
    df = query_df(sql, params or None)
    if not df.empty:
        df["preco"] = df["preco"].astype(float)
        df["cpf_vendedor"] = df["cpf_vendedor"].str.strip()
        for c in ["descricao_anuncio", "marca", "descricao_item", "foto", "tags"]:
            df[c] = df[c].astype(object).where(df[c].notna(), None)
    return df


def listar_categorias():
    return query_df("SELECT nome_categoria, nome_categoria_pai FROM categoria ORDER BY 1")


def criar_anuncio(cpf, d):
    def tx(cur):
        cur.execute(
            """INSERT INTO item (nome, marca, descricao, estado, reestocavel, nome_categoria)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_item""",
            (d["item"], d["marca"] or None, d["descricao_item"] or None,
             d["estado"], d["reestocavel"], d["categoria"]),
        )
        id_item = cur.fetchone()[0]

        for tag in d["tags"]:
            cur.execute("INSERT INTO tag (nome_tag) VALUES (%s) ON CONFLICT DO NOTHING", (tag,))
            cur.execute(
                "INSERT INTO item_tag (id_item, nome_tag) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (id_item, tag),
            )

        cur.execute(
            """INSERT INTO anuncio (cpf_vendedor, titulo, id_item, descricao, preco, tipo)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_anuncio""",
            (cpf, d["titulo"], id_item, d["descricao"] or None, d["preco"], d["tipo"]),
        )
        id_anuncio = cur.fetchone()[0]

        if d["tipo"] == "Empréstimo":
            cur.execute(
                "INSERT INTO emprestimo (id_anuncio, prazo) VALUES (%s, %s)",
                (id_anuncio, d["prazo"]),
            )
        for url in d["fotos"]:
            cur.execute(
                "INSERT INTO foto_anuncio (id_anuncio, url_foto) VALUES (%s, %s)",
                (id_anuncio, url),
            )
        return id_anuncio

    return run_tx(tx)


def criar_transacao(cpf_comprador, id_anuncio, valor, metodo_pag, metodo_ent):
    """Reserva o anúncio e cria transação + pagamento + entrega de forma atômica."""
    def tx(cur):
        cur.execute(
            """UPDATE anuncio SET status = 'Reservado'
               WHERE id_anuncio = %s AND status = 'Disponível' RETURNING id_anuncio""",
            (id_anuncio,),
        )
        if cur.fetchone() is None:
            return None  # alguém foi mais rápido
        cur.execute(
            """INSERT INTO transacao (cpf_comprador, id_anuncio, valor)
               VALUES (%s, %s, %s) RETURNING id_transacao""",
            (cpf_comprador, id_anuncio, valor),
        )
        id_t = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO pagamento (id_transacao, metodo, valor) VALUES (%s, %s, %s)",
            (id_t, metodo_pag, valor),
        )
        cur.execute(
            "INSERT INTO entrega (id_transacao, metodo) VALUES (%s, %s)",
            (id_t, metodo_ent),
        )
        return id_t

    return run_tx(tx)


def _finalizar_se_completo(cur, id_t):
    """Conclui a transação quando pagamento = Pago e entrega = Recebido."""
    cur.execute(
        """UPDATE transacao t SET status = 'Concluída'
           WHERE t.id_transacao = %s
             AND EXISTS (SELECT 1 FROM pagamento p
                         WHERE p.id_transacao = t.id_transacao AND p.status = 'Pago')
             AND EXISTS (SELECT 1 FROM entrega e
                         WHERE e.id_transacao = t.id_transacao AND e.status = 'Recebido')
           RETURNING t.id_anuncio""",
        (id_t,),
    )
    row = cur.fetchone()
    if row:
        cur.execute(
            "UPDATE anuncio SET status = 'Vendido' WHERE id_anuncio = %s AND tipo = 'Venda'",
            (row[0],),
        )


def pagar(id_t):
    def tx(cur):
        cur.execute(
            """UPDATE pagamento SET status = 'Pago', data_hora_pagamento = now()
               WHERE id_transacao = %s AND status = 'Pendente'""",
            (id_t,),
        )
        _finalizar_se_completo(cur, id_t)
    run_tx(tx)


def marcar_enviado(id_t):
    execute(
        """UPDATE entrega SET status = 'Enviado', data_hora_envio = now()
           WHERE id_transacao = %s AND status = 'Pendente'""",
        (id_t,),
    )


def confirmar_recebimento(id_t):
    def tx(cur):
        cur.execute(
            """UPDATE entrega SET status = 'Recebido', data_recebimento = now()
               WHERE id_transacao = %s AND status = 'Enviado'""",
            (id_t,),
        )
        _finalizar_se_completo(cur, id_t)
    run_tx(tx)


# ---------------------------------------------------------------
# Componentes reutilizáveis
# ---------------------------------------------------------------
def chat(id_anuncio, meu_cpf, outro_cpf, key):
    msgs = query_df(
        """SELECT m.cpf_remetente, m.texto, m.data_hora, u.nome
           FROM mensagem m JOIN usuario u ON u.cpf = m.cpf_remetente
           WHERE m.id_anuncio = %s
             AND ((m.cpf_remetente = %s AND m.cpf_destinatario = %s)
               OR (m.cpf_remetente = %s AND m.cpf_destinatario = %s))
           ORDER BY m.data_hora""",
        (id_anuncio, meu_cpf, outro_cpf, outro_cpf, meu_cpf),
    )
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
                execute(
                    """INSERT INTO mensagem (cpf_remetente, cpf_destinatario, id_anuncio, texto)
                       VALUES (%s, %s, %s, %s)""",
                    (meu_cpf, outro_cpf, id_anuncio, texto.strip()),
                )
                st.rerun()
            except psycopg2.Error as e:
                db_error(e)


def comentarios(id_anuncio):
    df = query_df(
        """SELECT c.texto, c.data_hora, u.nome
           FROM comentario c JOIN usuario u ON u.cpf = c.cpf_comentador
           WHERE c.id_anuncio = %s ORDER BY c.data_hora DESC""",
        (id_anuncio,),
    )
    user = current_user()
    if user:
        with st.form(f"form_coment_{id_anuncio}", clear_on_submit=True):
            texto = st.text_area("Comentar", height=80)
            if st.form_submit_button("Publicar comentário") and texto.strip():
                try:
                    execute(
                        """INSERT INTO comentario (cpf_comentador, id_anuncio, texto)
                           VALUES (%s, %s, %s)""",
                        (user["cpf"], id_anuncio, texto.strip()),
                    )
                    st.rerun()
                except psycopg2.Error as e:
                    db_error(e)
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


# ---------------------------------------------------------------
# Sidebar: conta
# ---------------------------------------------------------------
def sidebar_conta():
    with st.sidebar:
        st.title("🔁 Marketplace")
        user = current_user()
        if user:
            st.write(f"Olá, **{user['nome']}** 👋")
            if st.button("Sair", width="stretch"):
                del st.session_state["user"]
                st.rerun()
            return

        modo = st.radio("Conta", ["Entrar", "Cadastrar"], horizontal=True)
        if modo == "Entrar":
            email = st.text_input("E-mail")
            if st.button("Entrar", width="stretch"):
                df = query_df("SELECT * FROM usuario WHERE email = %s", (email.strip(),))
                if df.empty:
                    st.error("E-mail não encontrado.")
                else:
                    u = df.iloc[0].to_dict()
                    u["cpf"] = u["cpf"].strip()
                    st.session_state["user"] = u
                    st.rerun()
        else:
            limite = date.today() - timedelta(days=16 * 365 + 4)
            with st.form("cadastro"):
                cpf = st.text_input("CPF (11 dígitos, só números)", max_chars=11)
                nome = st.text_input("Nome")
                email = st.text_input("E-mail")
                nasc = st.date_input(
                    "Data de nascimento", value=limite,
                    min_value=date(1920, 1, 1), max_value=limite,
                )
                if st.form_submit_button("Cadastrar", width="stretch"):
                    if not (cpf.isdigit() and len(cpf) == 11):
                        st.error("CPF deve ter 11 dígitos.")
                    elif not nome.strip() or not email.strip():
                        st.error("Preencha nome e e-mail.")
                    else:
                        try:
                            execute(
                                """INSERT INTO usuario (cpf, nome, email, data_nascimento)
                                   VALUES (%s, %s, %s, %s)""",
                                (cpf, nome.strip(), email.strip(), nasc),
                            )
                            st.success("Cadastro feito! Agora é só entrar.")
                        except psycopg2.Error as e:
                            db_error(e)


# ---------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------
def pagina_loja():
    sel = st.session_state.get("anuncio_sel")
    if sel:
        return detalhe_anuncio(sel)

    st.header("🛍️ Anúncios disponíveis")
    df = buscar_anuncios()
    if df.empty:
        st.info("Nenhum anúncio disponível ainda.")
        return

    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    busca = c1.text_input("🔎 Buscar", placeholder="título, item, marca ou tag...")
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
        with cols[i % 3].container(border=True):
            if a["foto"]:
                st.image(a["foto"], width="stretch")
            st.subheader(a["titulo"])
            st.caption(f"{a['tipo']} · {a['estado']} · {a['nome_categoria']}")
            st.markdown(f"**{card_preco(a)}**")
            st.caption(f"Vendedor: {a['vendedor']}")
            if a["tags"]:
                st.caption("🏷️ " + a["tags"])
            if st.button("Ver detalhes", key=f"ver_{a['id_anuncio']}", width="stretch"):
                st.session_state["anuncio_sel"] = int(a["id_anuncio"])
                st.rerun()


def detalhe_anuncio(id_anuncio):
    if st.button("← Voltar"):
        st.session_state["anuncio_sel"] = None
        st.rerun()

    df = buscar_anuncios(apenas_disponiveis=False, id_anuncio=id_anuncio)
    if df.empty:
        st.error("Anúncio não encontrado.")
        return
    a = df.iloc[0]
    user = current_user()

    col_fotos, col_info = st.columns([1, 1])
    fotos = query_df(
        "SELECT url_foto FROM foto_anuncio WHERE id_anuncio = %s ORDER BY id_foto",
        (id_anuncio,),
    )
    with col_fotos:
        if fotos.empty:
            st.info("Sem fotos.")
        else:
            st.image(list(fotos["url_foto"]), width="stretch")

    with col_info:
        st.title(a["titulo"])
        st.markdown(f"## {card_preco(a)}")
        st.write(f"**Status:** {a['status']} · **Tipo:** {a['tipo']}")
        st.write(f"**Item:** {a['item']} ({a['marca'] or 'sem marca'}) · **Estado:** {a['estado']}")
        st.write(f"**Categoria:** {a['nome_categoria']}")
        if a["tags"]:
            st.write("🏷️ " + a["tags"])
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
            st.info("Este é o seu anúncio.")
        else:
            rotulo = "Solicitar empréstimo" if a["tipo"] == "Empréstimo" else "Comprar"
            with st.form(f"form_compra_{id_anuncio}"):
                metodo_pag = st.selectbox("Forma de pagamento", METODOS_PAGAMENTO)
                metodo_ent = st.selectbox("Forma de entrega", METODOS_ENTREGA)
                if st.form_submit_button(rotulo, width="stretch"):
                    try:
                        id_t = criar_transacao(
                            user["cpf"], id_anuncio, float(a["preco"]), metodo_pag, metodo_ent
                        )
                        if id_t:
                            st.success(f"Transação #{id_t} criada! Acompanhe em 'Minhas compras'.")
                        else:
                            st.error("Este anúncio acabou de ser reservado por outra pessoa.")
                    except psycopg2.Error as e:
                        db_error(e)

    tab_com, tab_msg = st.tabs(["💬 Comentários", "✉️ Mensagem ao vendedor"])
    with tab_com:
        comentarios(id_anuncio)
    with tab_msg:
        if user is None:
            st.caption("Entre na sua conta para enviar mensagens.")
        elif user["cpf"] == a["cpf_vendedor"]:
            st.caption("Responda mensagens na página 'Mensagens'.")
        else:
            chat(id_anuncio, user["cpf"], a["cpf_vendedor"], key=f"det_{id_anuncio}")


def pagina_anunciar():
    user = require_login()
    st.header("💰 Criar anúncio")

    cats = listar_categorias()
    with st.expander("➕ Nova categoria"):
        with st.form("nova_categoria", clear_on_submit=True):
            nome_cat = st.text_input("Nome da categoria")
            pai = st.selectbox("Categoria pai (opcional)", [""] + list(cats["nome_categoria"]))
            if st.form_submit_button("Criar") and nome_cat.strip():
                try:
                    execute(
                        "INSERT INTO categoria (nome_categoria, nome_categoria_pai) VALUES (%s, %s)",
                        (nome_cat.strip(), pai or None),
                    )
                    st.rerun()
                except psycopg2.Error as e:
                    db_error(e)

    if cats.empty:
        st.info("Crie ao menos uma categoria para poder anunciar.")
        return

    tipo = st.radio("Tipo de anúncio", TIPOS, horizontal=True)

    with st.form("novo_anuncio", clear_on_submit=True):
        st.subheader("Anúncio")
        titulo = st.text_input("Título")
        descricao = st.text_area("Descrição do anúncio")
        c1, c2 = st.columns(2)
        preco = c1.number_input("Preço (R$)", min_value=0.0, step=1.0)
        prazo = c2.number_input(
            "Prazo do empréstimo (dias)", min_value=1, step=1,
            disabled=(tipo != "Empréstimo"),
        )
        fotos = st.text_area("URLs das fotos (uma por linha)")

        st.subheader("Item")
        item = st.text_input("Nome do item")
        c3, c4 = st.columns(2)
        marca = c3.text_input("Marca")
        estado = c4.selectbox("Estado", ESTADOS)
        categoria = st.selectbox("Categoria", list(cats["nome_categoria"]))
        descricao_item = st.text_area("Descrição do item")
        tags = st.text_input("Tags (separadas por vírgula)")
        reestocavel = st.checkbox("Item reestocável")

        if st.form_submit_button("Publicar", width="stretch"):
            if not titulo.strip() or not item.strip():
                st.error("Título e nome do item são obrigatórios.")
            else:
                dados = {
                    "titulo": titulo.strip(), "descricao": descricao.strip(),
                    "preco": preco, "tipo": tipo, "prazo": int(prazo),
                    "fotos": [u.strip() for u in fotos.splitlines() if u.strip()],
                    "item": item.strip(), "marca": marca.strip(), "estado": estado,
                    "categoria": categoria, "descricao_item": descricao_item.strip(),
                    "reestocavel": reestocavel,
                    "tags": sorted({t.strip().lower() for t in tags.split(",") if t.strip()}),
                }
                try:
                    novo = criar_anuncio(user["cpf"], dados)
                    st.success(f"Anúncio #{novo} publicado!")
                except psycopg2.Error as e:
                    db_error(e)

    st.subheader("Meus anúncios")
    meus = query_df(
        """SELECT a.id_anuncio AS id, a.titulo, a.tipo, a.preco, a.status,
                  i.nome AS item, a.data_hora_publicacao AS publicado_em
           FROM anuncio a JOIN item i ON i.id_item = a.id_item
           WHERE a.cpf_vendedor = %s ORDER BY a.data_hora_publicacao DESC""",
        (user["cpf"],),
    )
    st.dataframe(meus, width="stretch", hide_index=True)


def pagina_mensagens():
    user = require_login()
    st.header("✉️ Mensagens")
    convs = query_df(
        """SELECT DISTINCT a.id_anuncio, a.titulo, u.cpf AS outro_cpf, u.nome AS outro_nome
           FROM mensagem m
           JOIN anuncio a ON a.id_anuncio = m.id_anuncio
           JOIN usuario u ON u.cpf = CASE WHEN m.cpf_remetente = %s
                                          THEN m.cpf_destinatario ELSE m.cpf_remetente END
           WHERE m.cpf_remetente = %s OR m.cpf_destinatario = %s""",
        (user["cpf"],) * 3,
    )
    if convs.empty:
        st.info("Você ainda não tem conversas.")
        return
    idx = st.selectbox(
        "Conversa", range(len(convs)),
        format_func=lambda i: f"{convs.iloc[i]['titulo']} — {convs.iloc[i]['outro_nome']}",
    )
    c = convs.iloc[idx]
    chat(int(c["id_anuncio"]), user["cpf"], c["outro_cpf"].strip(), key=f"inbox_{idx}")


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


def pagina_perfil():
    user = require_login()
    st.header("👤 Meu perfil")

    atual = query_df("SELECT * FROM usuario WHERE cpf = %s", (user["cpf"],)).iloc[0].to_dict()
    atual = {k: (None if pd.isna(v) else v) for k, v in atual.items()}
    media = query_df(
        "SELECT AVG(nota)::float AS media, COUNT(*) AS qtd FROM avaliacao WHERE cpf_avaliado = %s",
        (user["cpf"],),
    ).iloc[0]

    c1, c2 = st.columns([1, 3])
    with c1:
        if atual["foto"]:
            st.image(atual["foto"], width="stretch")
        else:
            st.markdown("# 🙂")
    with c2:
        st.subheader(atual["nome"])
        st.caption(atual["email"])
        if media["qtd"]:
            st.write(f"⭐ **{media['media']:.1f}** ({int(media['qtd'])} avaliações)")
        else:
            st.write("Sem avaliações ainda.")

    with st.form("editar_perfil"):
        nome = st.text_input("Nome", value=atual["nome"])
        foto = st.text_input("URL da foto", value=atual["foto"] or "")
        bio = st.text_area("Bio", value=atual["bio"] or "")
        if st.form_submit_button("Salvar"):
            try:
                execute(
                    "UPDATE usuario SET nome = %s, foto = %s, bio = %s WHERE cpf = %s",
                    (nome.strip(), foto.strip() or None, bio.strip() or None, user["cpf"]),
                )
                st.session_state["user"]["nome"] = nome.strip()
                st.success("Perfil atualizado!")
                st.rerun()
            except psycopg2.Error as e:
                db_error(e)

    st.subheader("💳 Meus cartões")
    cartoes = query_df("SELECT numero, metodo FROM cartao WHERE cpf = %s", (user["cpf"],))
    if cartoes.empty:
        st.caption("Nenhum cartão cadastrado.")
    else:
        cartoes["numero"] = "•••• " + cartoes["numero"].str[-4:]
        st.dataframe(cartoes, width="stretch", hide_index=True)

    with st.form("novo_cartao", clear_on_submit=True):
        numero = st.text_input("Número do cartão (13 a 19 dígitos)", max_chars=19)
        metodo = st.selectbox("Tipo", ["Crédito", "Débito"])
        if st.form_submit_button("Adicionar cartão"):
            try:
                execute(
                    "INSERT INTO cartao (cpf, numero, metodo) VALUES (%s, %s, %s)",
                    (user["cpf"], numero.strip(), metodo),
                )
                st.rerun()
            except psycopg2.Error as e:
                db_error(e)


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


# ---------------------------------------------------------------
# Navegação
# ---------------------------------------------------------------
sidebar_conta()

PAGINAS = {
    "🛍️ Loja": pagina_loja,
    "🔍 Busca avançada": pagina_busca,
    "💰 Anunciar": pagina_anunciar,
    "✉️ Mensagens": pagina_mensagens,
    "📦 Minhas compras": pagina_compras,
    "💼 Minhas vendas": pagina_vendas,
    "👤 Perfil": pagina_perfil,
    "📊 Dashboard": pagina_dashboard,
}
with st.sidebar:
    st.divider()
    escolha = st.radio("Navegação", list(PAGINAS), label_visibility="collapsed")

try:
    PAGINAS[escolha]()
except psycopg2.OperationalError as e:
    st.error("Não foi possível conectar ao banco. Verifique a DATABASE_URL.")
    st.caption(str(e))