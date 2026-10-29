# 🔁 Marketplace de compra, venda e empréstimo de itens

Aplicação web feita com **Streamlit** e **PostgreSQL (Neon)** para o Trabalho de Banco de Dados II (Parte 1),
sobre o banco de dados modelado em Banco de Dados I.

**Link da aplicação:** _(cole aqui o link do Streamlit Community Cloud)_

## Para que serve

Pessoas anunciam itens para **venda** ou **empréstimo**, conversam, comentam, compram, pagam, acompanham a
entrega e avaliam o vendedor. Um **dashboard analítico** mostra como o mercado se comporta.

## Temas do trabalho atendidos

- **Buscas complexas de forma simplificada + inserção de dados** (páginas Loja, Busca avançada, Anunciar, etc.)
- **Análise visual e estatística** (página Dashboard, com 4 abas e mais de 15 consultas)

## Páginas

| Página | O que faz | Tabelas envolvidas |
|---|---|---|
| Loja | Lista anúncios com filtros; detalhe com fotos, comentários e chat; compra/empréstimo | anuncio, item, usuario, foto_anuncio, item_tag, emprestimo, comentario, mensagem |
| Busca avançada | Filtros combinados: texto, categoria **com subcategorias (CTE recursiva)**, tags (todas), estado, tipo, preço, nota do vendedor, data | anuncio, item, categoria, item_tag, usuario, avaliacao, comentario |
| Anunciar | Cria item, tags, anúncio, empréstimo e fotos **em uma única transação** | item, tag, item_tag, anuncio, emprestimo, foto_anuncio, categoria |
| Mensagens | Caixa de entrada por anúncio | mensagem, anuncio, usuario |
| Minhas compras / vendas | Pagamento, envio, recebimento, avaliação e suporte | transacao, pagamento, entrega, avaliacao, suporte |
| Perfil | Dados, nota média e cartões | usuario, avaliacao, cartao |
| Dashboard | Análises (ver abaixo) | todas |

### Técnicas de SQL usadas

`JOIN` de até 4 tabelas, `LEFT JOIN`, subconsultas correlacionadas, `WITH RECURSIVE` (hierarquia de categorias),
CTEs, funções de janela (`AVG() OVER` — média móvel), `GROUP BY` / `HAVING`, `FILTER`, `UNION ALL`,
`CASE`, `date_trunc`, `age()`, `string_agg`, `ANY(array)` e transações atômicas (`UPDATE ... RETURNING`).

## Rodando localmente

```bash
git clone <url-do-repositorio>
cd <pasta>
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # preencha DATABASE_URL (string do Neon)
streamlit run app.py
```

## Deploy (Streamlit Community Cloud)

1. Suba `app.py`, `requirements.txt`, `.gitignore` e `README.md` para o GitHub (**nunca** o `.env`).
2. Em share.streamlit.io: *New app* → escolha o repositório, branch `main`, arquivo `app.py`.
3. Em *Advanced settings → Secrets*, cole: `DATABASE_URL = "postgresql://...neon.tech/neondb?sslmode=require"`

## Observações

- O login é apenas por e-mail (demonstração acadêmica), pois o modelo não possui senha.
- O pagamento é simulado por um botão; não há integração com gateway.