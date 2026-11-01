"""Configuração: conexão com o banco e constantes do domínio."""
import os
from pathlib import Path
from urllib.parse import quote_plus

import streamlit as st
from dotenv import load_dotenv

# Procura o .env sempre na raiz do projeto, ao lado do app.py (não importa de onde o comando foi rodado)
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)
DATABASE_URL = os.getenv("DATABASE_URL")

# Formato alternativo: variáveis separadas (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT)
if not DATABASE_URL and os.getenv("DB_HOST"):
    DATABASE_URL = (
        f"postgresql://{quote_plus(os.getenv('DB_USER', ''))}:{quote_plus(os.getenv('DB_PASSWORD', ''))}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'neondb')}"
        "?sslmode=require"
    )

if not DATABASE_URL:  # alternativa: Secrets do Streamlit (.streamlit/secrets.toml)
    try:
        DATABASE_URL = st.secrets.get("DATABASE_URL")
    except Exception:
        DATABASE_URL = None

if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.strip().strip('"').strip("'")

ESTADOS = ["Novo", "Quase Novo", "Usado", "Razoável", "Com avarias"]
TIPOS = ["Venda", "Empréstimo"]
METODOS_PAGAMENTO = ["Pix", "Boleto", "Crédito", "Débito"]
METODOS_ENTREGA = ["Retirada em mãos", "Correios", "Transportadora"]

TABELAS_ESPERADAS = [
    "usuario", "cartao", "categoria", "item", "tag", "item_tag", "anuncio", "emprestimo",
    "foto_anuncio", "comentario", "mensagem", "suporte", "avaliacao", "transacao",
    "pagamento", "entrega",
]
