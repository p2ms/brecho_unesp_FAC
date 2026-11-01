"""Acesso ao banco: conexão, consultas e transações."""
import pandas as pd
import psycopg2
import streamlit as st

from .config import DATABASE_URL


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
