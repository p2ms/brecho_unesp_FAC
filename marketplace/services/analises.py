"""Consultas analíticas usadas pelo Dashboard."""
from ..db import query_df


def indicadores_gerais():
    return query_df(
        """SELECT
             (SELECT COUNT(*) FROM usuario) AS usuarios,
             (SELECT COUNT(*) FROM anuncio WHERE status = 'Disponível') AS disponiveis,
             (SELECT COUNT(*) FROM transacao WHERE status = 'Concluída') AS concluidas,
             (SELECT COALESCE(SUM(valor), 0)::float FROM transacao
               WHERE status = 'Concluída') AS volume"""
    ).iloc[0]


def anuncios_por_categoria():
    return query_df(
        """SELECT i.nome_categoria AS categoria, COUNT(*) AS anuncios
           FROM anuncio a JOIN item i ON i.id_item = a.id_item
           GROUP BY 1 ORDER BY 2 DESC"""
    )


def anuncios_por_status():
    return query_df("SELECT status, COUNT(*) AS qtd FROM anuncio GROUP BY 1")


def publicacoes_por_semana():
    return query_df(
        """WITH semanal AS (
               SELECT date_trunc('week', data_hora_publicacao)::date AS semana,
                      COUNT(*) AS anuncios
               FROM anuncio GROUP BY 1)
           SELECT semana, anuncios,
                  AVG(anuncios) OVER (ORDER BY semana
                      ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)::float AS media_movel_3_semanas
           FROM semanal ORDER BY semana"""
    )


def preco_por_categoria_raiz():
    return query_df(
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
    )


def precos_por_estado():
    return query_df(
        """SELECT i.estado, a.preco::float AS preco
           FROM anuncio a JOIN item i ON i.id_item = a.id_item
           WHERE a.tipo = 'Venda'"""
    )


def categoria_por_estado():
    return query_df(
        """SELECT i.nome_categoria AS categoria, i.estado, COUNT(*) AS qtd
           FROM anuncio a JOIN item i ON i.id_item = a.id_item GROUP BY 1, 2"""
    )


def tags_mais_usadas():
    return query_df(
        """SELECT t.nome_tag AS tag, COUNT(DISTINCT a.id_anuncio) AS anuncios
           FROM item_tag t JOIN anuncio a ON a.id_item = t.id_item
           GROUP BY 1 ORDER BY 2 DESC LIMIT 10"""
    )


def conversao_por_categoria():
    return query_df(
        """SELECT i.nome_categoria AS categoria, COUNT(*) AS total,
                  COUNT(*) FILTER (WHERE a.status = 'Vendido') AS vendidos,
                  ROUND(100.0 * COUNT(*) FILTER (WHERE a.status = 'Vendido')
                        / COUNT(*), 1)::float AS taxa_conversao
           FROM anuncio a JOIN item i ON i.id_item = a.id_item
           GROUP BY 1 ORDER BY 4 DESC"""
    )


def usuarios_por_faixa_etaria():
    return query_df(
        """SELECT CASE WHEN idade < 20 THEN '16-19' WHEN idade < 30 THEN '20-29'
                       WHEN idade < 40 THEN '30-39' WHEN idade < 50 THEN '40-49'
                       ELSE '50+' END AS faixa, COUNT(*) AS usuarios
           FROM (SELECT EXTRACT(YEAR FROM age(data_nascimento))::int AS idade
                 FROM usuario) s
           GROUP BY 1 ORDER BY 1"""
    )


def melhores_vendedores():
    return query_df(
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


def atividade_usuarios():
    return query_df(
        """SELECT u.nome, x.acao, COUNT(*) AS qtd FROM (
               SELECT cpf_vendedor AS cpf, 'Anúncios' AS acao FROM anuncio
               UNION ALL SELECT cpf_comentador, 'Comentários' FROM comentario
               UNION ALL SELECT cpf_remetente, 'Mensagens' FROM mensagem
               UNION ALL SELECT cpf_comprador, 'Compras' FROM transacao
           ) x JOIN usuario u ON u.cpf = x.cpf
           GROUP BY u.nome, x.acao"""
    )


def funil_transacoes():
    return query_df(
        """SELECT COUNT(*) AS criadas,
                  COUNT(*) FILTER (WHERE p.status = 'Pago') AS pagas,
                  COUNT(*) FILTER (WHERE e.status IN ('Enviado', 'Recebido')) AS enviadas,
                  COUNT(*) FILTER (WHERE e.status = 'Recebido') AS recebidas,
                  COUNT(*) FILTER (WHERE t.status = 'Concluída') AS concluidas
           FROM transacao t
           JOIN pagamento p ON p.id_transacao = t.id_transacao
           JOIN entrega e ON e.id_transacao = t.id_transacao"""
    ).iloc[0]


def metodos_pagamento():
    return query_df(
        "SELECT metodo, COUNT(*) AS qtd, SUM(valor)::float AS valor FROM pagamento GROUP BY 1"
    )


def tempos_transacao():
    return query_df(
        """SELECT AVG(EXTRACT(EPOCH FROM (p.data_hora_pagamento - t.data_hora)) / 3600)::float AS pag,
                  AVG(EXTRACT(EPOCH FROM (e.data_hora_envio - p.data_hora_pagamento)) / 3600)::float AS env,
                  AVG(EXTRACT(EPOCH FROM (e.data_recebimento - e.data_hora_envio)) / 3600)::float AS rec
           FROM transacao t
           JOIN pagamento p ON p.id_transacao = t.id_transacao
           JOIN entrega e ON e.id_transacao = t.id_transacao"""
    ).iloc[0]


def chamados_por_categoria():
    return query_df(
        """SELECT i.nome_categoria AS categoria, s.status, COUNT(*) AS chamados
           FROM suporte s
           JOIN anuncio a ON a.id_anuncio = s.id_anuncio
           JOIN item i ON i.id_item = a.id_item
           GROUP BY 1, 2"""
    )
