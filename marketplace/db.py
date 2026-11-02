"""Acesso ao banco: conexão, consultas e transações."""
from contextlib import contextmanager

import pandas as pd
import psycopg2

from .config import DATABASE_URL
from .erros import ConexaoFalhou, ErroBanco, TabelaAusente


def get_conn():
    # Uma conexão por operação: o Neon derruba conexões ociosas.
    return psycopg2.connect(DATABASE_URL)


def _mensagem(e):
    msg = getattr(getattr(e, "diag", None), "message_primary", None) or str(e)
    return f"Erro no banco de dados: {msg}"


@contextmanager
def _traduzir_erros():
    """Converte erros do psycopg2 nos erros da aplicação."""
    try:
        yield
    except psycopg2.errors.UndefinedTable as e:
        raise TabelaAusente(_mensagem(e)) from e
    except psycopg2.OperationalError as e:
        raise ConexaoFalhou("Não foi possível conectar ao banco. Verifique a DATABASE_URL.") from e
    except psycopg2.Error as e:
        raise ErroBanco(_mensagem(e)) from e


def query_df(sql, params=None):
    """SELECT -> DataFrame"""
    with _traduzir_erros():
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
    with _traduzir_erros():
        conn = get_conn()
        try:
            with conn, conn.cursor() as cur:
                cur.execute(sql, params)
        finally:
            conn.close()


def run_tx(fn):
    """Executa fn(cur) em uma única transação (commit/rollback automáticos)."""
    with _traduzir_erros():
        conn = get_conn()
        try:
            with conn, conn.cursor() as cur:
                return fn(cur)
        finally:
            conn.close()
