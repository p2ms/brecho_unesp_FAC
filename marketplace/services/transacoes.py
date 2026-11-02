"""Ciclo da transação: compra, pagamento, entrega, avaliação e suporte.

As operações recebem o CPF de quem as solicita e conferem a permissão aqui,
sem depender de a tela ter mostrado o botão só para a pessoa certa.
"""
from ..db import query_df, run_tx
from ..erros import ErroValidacao, NaoAutorizado


def _dados_transacao(cur, id_t):
    cur.execute(
        """SELECT t.cpf_comprador, a.cpf_vendedor, t.id_anuncio, t.status
           FROM transacao t JOIN anuncio a ON a.id_anuncio = t.id_anuncio
           WHERE t.id_transacao = %s""",
        (id_t,),
    )
    row = cur.fetchone()
    if row is None:
        raise ErroValidacao("Transação não encontrada.")
    return {
        "comprador": row[0].strip(), "vendedor": row[1].strip(),
        "id_anuncio": row[2], "status": row[3],
    }


def _exigir_comprador(cur, id_t, cpf):
    dados = _dados_transacao(cur, id_t)
    if dados["comprador"] != cpf:
        raise NaoAutorizado("Apenas o comprador pode realizar esta operação.")
    return dados


def _exigir_vendedor(cur, id_t, cpf):
    dados = _dados_transacao(cur, id_t)
    if dados["vendedor"] != cpf:
        raise NaoAutorizado("Apenas o vendedor pode realizar esta operação.")
    return dados


def criar_transacao(cpf_comprador, id_anuncio, metodo_pag, metodo_ent):
    """Reserva o anúncio e cria transação + pagamento + entrega de forma atômica."""
    def tx(cur):
        cur.execute(
            """UPDATE anuncio SET status = 'Reservado'
               WHERE id_anuncio = %s AND status = 'Disponível'
               RETURNING cpf_vendedor, preco""",
            (id_anuncio,),
        )
        row = cur.fetchone()
        if row is None:
            return None  # alguém foi mais rápido
        cpf_vendedor, valor = row
        if cpf_vendedor.strip() == cpf_comprador:
            raise NaoAutorizado("Você não pode comprar o seu próprio anúncio.")
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


def pagar(id_t, cpf):
    def tx(cur):
        _exigir_comprador(cur, id_t, cpf)
        cur.execute(
            """UPDATE pagamento SET status = 'Pago', data_hora_pagamento = now()
               WHERE id_transacao = %s AND status = 'Pendente'""",
            (id_t,),
        )
        _finalizar_se_completo(cur, id_t)
    run_tx(tx)


def marcar_enviado(id_t, cpf):
    def tx(cur):
        _exigir_vendedor(cur, id_t, cpf)
        cur.execute(
            """UPDATE entrega SET status = 'Enviado', data_hora_envio = now()
               WHERE id_transacao = %s AND status = 'Pendente'""",
            (id_t,),
        )
    run_tx(tx)


def confirmar_recebimento(id_t, cpf):
    def tx(cur):
        _exigir_comprador(cur, id_t, cpf)
        cur.execute(
            """UPDATE entrega SET status = 'Recebido', data_recebimento = now()
               WHERE id_transacao = %s AND status = 'Enviado'""",
            (id_t,),
        )
        _finalizar_se_completo(cur, id_t)
    run_tx(tx)


def avaliar_vendedor(id_t, cpf, nota):
    def tx(cur):
        dados = _exigir_comprador(cur, id_t, cpf)
        if dados["status"] != "Concluída":
            raise ErroValidacao("Só é possível avaliar depois que a transação for concluída.")
        cur.execute(
            """INSERT INTO avaliacao (cpf_avaliador, cpf_avaliado, nota)
               VALUES (%s, %s, %s)""",
            (cpf, dados["vendedor"], nota),
        )
    run_tx(tx)


def abrir_chamado(id_t, cpf, descricao):
    def tx(cur):
        dados = _exigir_comprador(cur, id_t, cpf)
        cur.execute(
            """INSERT INTO suporte (id_anuncio, cpf_cliente, descricao)
               VALUES (%s, %s, %s)""",
            (dados["id_anuncio"], cpf, descricao.strip()),
        )
    run_tx(tx)


def listar_transacoes(cpf, papel):
    """papel = 'comprador' ou 'vendedor'"""
    filtro = "t.cpf_comprador" if papel == "comprador" else "a.cpf_vendedor"
    outro = (
        "(SELECT nome FROM usuario WHERE cpf = a.cpf_vendedor)"
        if papel == "comprador"
        else "(SELECT nome FROM usuario WHERE cpf = t.cpf_comprador)"
    )
    return query_df(
        f"""SELECT t.id_transacao, t.data_hora, t.valor, t.status AS status_transacao,
                   a.id_anuncio, a.titulo, a.tipo, a.cpf_vendedor, {outro} AS outra_parte,
                   p.status AS pagamento, p.metodo AS metodo_pagamento,
                   e.status AS entrega, e.metodo AS metodo_entrega
            FROM transacao t
            JOIN anuncio a ON a.id_anuncio = t.id_anuncio
            JOIN pagamento p ON p.id_transacao = t.id_transacao
            JOIN entrega e ON e.id_transacao = t.id_transacao
            WHERE {filtro} = %s ORDER BY t.data_hora DESC""",
        (cpf,),
    )


def listar_chamados(cpf):
    return query_df(
        """SELECT s.id_suporte AS id, a.titulo AS anuncio, s.descricao, s.status, s.data_hora
           FROM suporte s JOIN anuncio a ON a.id_anuncio = s.id_anuncio
           WHERE s.cpf_cliente = %s ORDER BY s.data_hora DESC""",
        (cpf,),
    )
