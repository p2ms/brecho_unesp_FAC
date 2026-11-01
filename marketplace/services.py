"""Consultas e operações de negócio (anúncios e transações)."""
from .db import execute, query_df, run_tx


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
