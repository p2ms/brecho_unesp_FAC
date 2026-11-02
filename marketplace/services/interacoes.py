"""Mensagens privadas e comentários públicos dos anúncios."""
from ..db import execute, query_df


def listar_mensagens(id_anuncio, meu_cpf, outro_cpf):
    return query_df(
        """SELECT m.cpf_remetente, m.texto, m.data_hora, u.nome
           FROM mensagem m JOIN usuario u ON u.cpf = m.cpf_remetente
           WHERE m.id_anuncio = %s
             AND ((m.cpf_remetente = %s AND m.cpf_destinatario = %s)
               OR (m.cpf_remetente = %s AND m.cpf_destinatario = %s))
           ORDER BY m.data_hora""",
        (id_anuncio, meu_cpf, outro_cpf, outro_cpf, meu_cpf),
    )


def enviar_mensagem(cpf_remetente, cpf_destinatario, id_anuncio, texto):
    execute(
        """INSERT INTO mensagem (cpf_remetente, cpf_destinatario, id_anuncio, texto)
           VALUES (%s, %s, %s, %s)""",
        (cpf_remetente, cpf_destinatario, id_anuncio, texto.strip()),
    )


def listar_conversas(cpf):
    return query_df(
        """SELECT DISTINCT a.id_anuncio, a.titulo, u.cpf AS outro_cpf, u.nome AS outro_nome
           FROM mensagem m
           JOIN anuncio a ON a.id_anuncio = m.id_anuncio
           JOIN usuario u ON u.cpf = CASE WHEN m.cpf_remetente = %s
                                          THEN m.cpf_destinatario ELSE m.cpf_remetente END
           WHERE m.cpf_remetente = %s OR m.cpf_destinatario = %s""",
        (cpf,) * 3,
    )


def listar_comentarios(id_anuncio):
    return query_df(
        """SELECT c.texto, c.data_hora, u.nome
           FROM comentario c JOIN usuario u ON u.cpf = c.cpf_comentador
           WHERE c.id_anuncio = %s ORDER BY c.data_hora DESC""",
        (id_anuncio,),
    )


def publicar_comentario(cpf, id_anuncio, texto):
    execute(
        """INSERT INTO comentario (cpf_comentador, id_anuncio, texto)
           VALUES (%s, %s, %s)""",
        (cpf, id_anuncio, texto.strip()),
    )
