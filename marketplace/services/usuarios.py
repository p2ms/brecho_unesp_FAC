"""Usuários: login, cadastro, perfil e cartões."""
import pandas as pd

from ..db import execute, query_df
from ..erros import ErroValidacao


def buscar_por_email(email):
    df = query_df("SELECT * FROM usuario WHERE email = %s", (email.strip(),))
    if df.empty:
        return None
    u = df.iloc[0].to_dict()
    u["cpf"] = u["cpf"].strip()
    return u


def cadastrar(cpf, nome, email, data_nascimento):
    if not (cpf.isdigit() and len(cpf) == 11):
        raise ErroValidacao("CPF deve ter 11 dígitos.")
    if not nome.strip() or not email.strip():
        raise ErroValidacao("Preencha nome e e-mail.")
    execute(
        """INSERT INTO usuario (cpf, nome, email, data_nascimento)
           VALUES (%s, %s, %s, %s)""",
        (cpf, nome.strip(), email.strip(), data_nascimento),
    )


def obter_perfil(cpf):
    atual = query_df("SELECT * FROM usuario WHERE cpf = %s", (cpf,)).iloc[0].to_dict()
    return {k: (None if pd.isna(v) else v) for k, v in atual.items()}


def nota_media(cpf):
    return query_df(
        "SELECT AVG(nota)::float AS media, COUNT(*) AS qtd FROM avaliacao WHERE cpf_avaliado = %s",
        (cpf,),
    ).iloc[0]


def atualizar_perfil(cpf, nome, foto, bio):
    execute(
        "UPDATE usuario SET nome = %s, foto = %s, bio = %s WHERE cpf = %s",
        (nome.strip(), foto.strip() or None, bio.strip() or None, cpf),
    )


def listar_cartoes(cpf):
    """Cartões do usuário, só com os 4 últimos dígitos visíveis."""
    cartoes = query_df("SELECT numero, metodo FROM cartao WHERE cpf = %s", (cpf,))
    if not cartoes.empty:
        cartoes["numero"] = "•••• " + cartoes["numero"].str[-4:]
    return cartoes


def adicionar_cartao(cpf, numero, metodo):
    execute(
        "INSERT INTO cartao (cpf, numero, metodo) VALUES (%s, %s, %s)",
        (cpf, numero.strip(), metodo),
    )
