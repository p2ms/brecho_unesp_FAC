"""Anúncios, itens, categorias, tags e busca."""
from . import armazenamento
from ..db import execute, query_df, run_tx
from ..erros import ErroValidacao, NaoAutorizado

ORDENS_BUSCA = {
    "Mais recentes": "a.data_hora_publicacao DESC",
    "Menor preço": "a.preco ASC",
    "Maior preço": "a.preco DESC",
    "Melhor avaliados": "nota_vendedor DESC, avaliacoes DESC",
    "Mais comentados": "comentarios DESC",
}


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


def listar_fotos(id_anuncio):
    return query_df(
        "SELECT url_foto FROM foto_anuncio WHERE id_anuncio = %s ORDER BY id_foto",
        (id_anuncio,),
    )


def listar_do_vendedor(cpf):
    return query_df(
        """SELECT a.id_anuncio AS id, a.titulo, a.tipo, a.preco, a.status,
                  i.nome AS item, a.data_hora_publicacao AS publicado_em,
                  a.status <> 'Disponível' OR EXISTS (
                      SELECT 1 FROM transacao t WHERE t.id_anuncio = a.id_anuncio
                  ) AS bloqueado
           FROM anuncio a JOIN item i ON i.id_item = a.id_item
           WHERE a.cpf_vendedor = %s ORDER BY a.data_hora_publicacao DESC""",
        (cpf,),
    )


def listar_categorias():
    return query_df("SELECT nome_categoria, nome_categoria_pai FROM categoria ORDER BY 1")


def criar_categoria(nome, pai=None):
    execute(
        "INSERT INTO categoria (nome_categoria, nome_categoria_pai) VALUES (%s, %s)",
        (nome.strip(), pai or None),
    )


def listar_tags():
    return query_df("SELECT nome_tag FROM tag ORDER BY 1")


def preco_maximo():
    return float(query_df("SELECT COALESCE(MAX(preco), 0)::float AS m FROM anuncio").iloc[0]["m"])


def criar_anuncio(cpf, d):
    if not d["titulo"].strip() or not d["item"].strip():
        raise ErroValidacao("Título e nome do item são obrigatórios.")
    tags = sorted({t.strip().lower() for t in d["tags"] if t.strip()})
    urls = armazenamento.enviar_fotos(d["fotos"])

    def tx(cur):
        cur.execute(
            """INSERT INTO item (nome, marca, descricao, estado, reestocavel, nome_categoria)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_item""",
            (d["item"], d["marca"] or None, d["descricao_item"] or None,
             d["estado"], d["reestocavel"], d["categoria"]),
        )
        id_item = cur.fetchone()[0]

        for tag in tags:
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
        for url in urls:
            cur.execute(
                "INSERT INTO foto_anuncio (id_anuncio, url_foto) VALUES (%s, %s)",
                (id_anuncio, url),
            )
        return id_anuncio

    try:
        return run_tx(tx)
    except Exception:  # a transação foi desfeita: as fotos enviadas ficariam sem anúncio
        armazenamento.remover_fotos(urls)
        raise


def _anuncio_alteravel(cur, cpf, id_anuncio):
    """Trava o anúncio e confere se ele é de quem pediu e se ainda não entrou em nenhuma transação."""
    cur.execute(
        """SELECT a.cpf_vendedor, a.status, a.id_item, a.tipo,
                  EXISTS (SELECT 1 FROM transacao t WHERE t.id_anuncio = a.id_anuncio)
           FROM anuncio a WHERE a.id_anuncio = %s FOR UPDATE""",
        (id_anuncio,),
    )
    linha = cur.fetchone()
    if linha is None:
        raise ErroValidacao("Anúncio não encontrado.")
    vendedor, status, id_item, tipo, tem_transacao = linha
    if vendedor.strip() != cpf:
        raise NaoAutorizado("Só quem publicou o anúncio pode alterá-lo.")
    if status != "Disponível" or tem_transacao:
        raise ErroValidacao("Anúncios que já entraram em uma transação não podem ser alterados.")
    return id_item, tipo


def _contar_fotos(cur, id_anuncio, removidas):
    cur.execute(
        "SELECT COUNT(*) FROM foto_anuncio WHERE id_anuncio = %s AND NOT url_foto = ANY(%s)",
        (id_anuncio, list(removidas)),
    )
    return cur.fetchone()[0]


def editar_anuncio(cpf, id_anuncio, d):
    if not d["titulo"].strip() or not d["item"].strip():
        raise ErroValidacao("Título e nome do item são obrigatórios.")
    tags = sorted({t.strip().lower() for t in d["tags"] if t.strip()})
    removidas = d["fotos_removidas"]

    def conferir(cur):
        _anuncio_alteravel(cur, cpf, id_anuncio)
        if _contar_fotos(cur, id_anuncio, removidas) + len(d["fotos_novas"]) > armazenamento.MAX_FOTOS:
            raise ErroValidacao(f"Um anúncio pode ter no máximo {armazenamento.MAX_FOTOS} fotos.")

    run_tx(conferir)  # antes do envio, para não subir fotos de uma edição que seria recusada
    urls = armazenamento.enviar_fotos(d["fotos_novas"])

    def tx(cur):
        id_item, tipo = _anuncio_alteravel(cur, cpf, id_anuncio)
        cur.execute(
            "UPDATE anuncio SET titulo = %s, descricao = %s, preco = %s WHERE id_anuncio = %s",
            (d["titulo"].strip(), d["descricao"].strip() or None, d["preco"], id_anuncio),
        )
        cur.execute(
            """UPDATE item SET nome = %s, marca = %s, descricao = %s, estado = %s, nome_categoria = %s
               WHERE id_item = %s""",
            (d["item"].strip(), d["marca"].strip() or None, d["descricao_item"].strip() or None,
             d["estado"], d["categoria"], id_item),
        )
        if tipo == "Empréstimo":
            cur.execute("UPDATE emprestimo SET prazo = %s WHERE id_anuncio = %s", (d["prazo"], id_anuncio))

        cur.execute("DELETE FROM item_tag WHERE id_item = %s", (id_item,))
        for tag in tags:
            cur.execute("INSERT INTO tag (nome_tag) VALUES (%s) ON CONFLICT DO NOTHING", (tag,))
            cur.execute("INSERT INTO item_tag (id_item, nome_tag) VALUES (%s, %s)", (id_item, tag))

        cur.execute(
            "DELETE FROM foto_anuncio WHERE id_anuncio = %s AND url_foto = ANY(%s) RETURNING url_foto",
            (id_anuncio, list(removidas)),
        )
        apagadas = [linha[0] for linha in cur.fetchall()]
        for url in urls:
            cur.execute(
                "INSERT INTO foto_anuncio (id_anuncio, url_foto) VALUES (%s, %s)",
                (id_anuncio, url),
            )
        return apagadas

    try:
        apagadas = run_tx(tx)
    except Exception:
        armazenamento.remover_fotos(urls)
        raise
    armazenamento.remover_fotos(apagadas)


def apagar_anuncio(cpf, id_anuncio):
    """Apaga o anúncio, o que depende dele no banco (fotos, comentários, mensagens) e o item sem outro anúncio."""

    def tx(cur):
        id_item, _ = _anuncio_alteravel(cur, cpf, id_anuncio)
        cur.execute("SELECT url_foto FROM foto_anuncio WHERE id_anuncio = %s", (id_anuncio,))
        fotos = [linha[0] for linha in cur.fetchall()]
        cur.execute("DELETE FROM anuncio WHERE id_anuncio = %s", (id_anuncio,))
        cur.execute(
            """DELETE FROM item i WHERE i.id_item = %s
               AND NOT EXISTS (SELECT 1 FROM anuncio a WHERE a.id_item = i.id_item)""",
            (id_item,),
        )
        return fotos

    armazenamento.remover_fotos(run_tx(tx))


def busca_avancada(texto="", categoria="", tags=(), estados=(), tipo="Todos", nota_min=0.0,
                   faixa=(0.0, 0.0), dias=0, ordem="Mais recentes"):
    """Retorna (DataFrame, SQL gerado) dos anúncios disponíveis que atendem aos filtros."""
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
               e.prazo,
               (SELECT url_foto FROM foto_anuncio f
                 WHERE f.id_anuncio = a.id_anuncio ORDER BY f.id_foto LIMIT 1) AS foto,
               COALESCE(n.nota_media, 0) AS nota_vendedor,
               COALESCE(n.n, 0) AS avaliacoes,
               (SELECT COUNT(*) FROM comentario c WHERE c.id_anuncio = a.id_anuncio) AS comentarios,
               (SELECT string_agg(t.nome_tag, ', ') FROM item_tag t
                 WHERE t.id_item = i.id_item) AS tags,
               a.data_hora_publicacao AS publicado_em
        FROM anuncio a
        JOIN item i ON i.id_item = a.id_item
        JOIN usuario u ON u.cpf = a.cpf_vendedor
        LEFT JOIN emprestimo e ON e.id_anuncio = a.id_anuncio
        LEFT JOIN nota n ON n.cpf_avaliado = a.cpf_vendedor
        WHERE a.status = 'Disponível' AND a.preco BETWEEN %s AND %s
    """
    params += [faixa[0], faixa[1]]

    if categoria:
        sql += " AND i.nome_categoria IN (SELECT nome_categoria FROM cat)"
    if texto.strip():
        sql += """ AND (a.titulo ILIKE %s OR i.nome ILIKE %s OR i.marca ILIKE %s
                        OR EXISTS (SELECT 1 FROM item_tag t
                                   WHERE t.id_item = i.id_item AND t.nome_tag ILIKE %s))"""
        params += [f"%{texto.strip()}%"] * 4
    if tags:
        sql += """ AND (SELECT COUNT(DISTINCT t.nome_tag) FROM item_tag t
                        WHERE t.id_item = i.id_item AND t.nome_tag = ANY(%s)) = %s"""
        params += [list(tags), len(tags)]
    if estados:
        sql += " AND i.estado = ANY(%s)"
        params.append(list(estados))
    if tipo != "Todos":
        sql += " AND a.tipo = %s"
        params.append(tipo)
    if nota_min > 0:
        sql += " AND COALESCE(n.nota_media, 0) >= %s"
        params.append(nota_min)
    if dias > 0:
        sql += " AND a.data_hora_publicacao >= now() - make_interval(days => %s)"
        params.append(int(dias))
    sql += f" ORDER BY {ORDENS_BUSCA[ordem]}"

    return query_df(sql, params), sql
