"""Consultas de diagnóstico: onde o app está conectado e quais tabelas enxerga."""
from urllib.parse import urlparse

from ..config import DATABASE_URL
from ..db import query_df


def info_conexao():
    info = query_df(
        "SELECT current_database() AS banco, current_user AS usuario, current_schema() AS esquema"
    ).iloc[0].to_dict()
    info["host"] = urlparse(DATABASE_URL).hostname
    return info


def listar_tabelas():
    return query_df(
        """SELECT table_schema AS esquema, table_name AS tabela
           FROM information_schema.tables
           WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
           ORDER BY 1, 2"""
    )
