# Brechó da Unesp

Marketplace de compra, venda e empréstimo de itens.

Aplicação web feita com **Streamlit** e **PostgreSQL (Supabase)** para o Trabalho de Banco de Dados II (Parte 1),
sobre o banco de dados modelado em Banco de Dados I.

**Link da aplicação:** _(cole aqui o link do Streamlit Community Cloud)_

## Para que serve

Pessoas anunciam itens para **venda** ou **empréstimo**, conversam, comentam, compram, pagam, acompanham a
entrega e avaliam o vendedor. Um **dashboard analítico** mostra como o mercado se comporta.

## Temas do trabalho atendidos

- **Buscas complexas de forma simplificada + inserção de dados** (páginas Loja, Anunciar, Minha loja, etc.)
- **Análise visual e estatística** (página Painel, com 4 abas e mais de 15 consultas)

## Páginas

| Página | O que faz | Tabelas envolvidas |
|---|---|---|
| Loja | Vitrine com busca e "Mais filtros" combinados: texto, categoria **com subcategorias (CTE recursiva)**, tags (todas), estado, tipo, preço, nota do vendedor e data; mostra o SQL gerado | anuncio, item, categoria, item_tag, usuario, avaliacao, comentario, foto_anuncio, emprestimo |
| Anúncio | Detalhe com fotos, comentários e chat; compra/empréstimo | anuncio, item, usuario, foto_anuncio, item_tag, emprestimo, comentario, mensagem, transacao |
| Anunciar | Cria item, tags, anúncio, empréstimo e fotos **em uma única transação** | item, tag, item_tag, anuncio, emprestimo, foto_anuncio, categoria |
| Mensagens | Caixa de entrada por anúncio | mensagem, anuncio, usuario |
| Minha loja | Edita e apaga os próprios anúncios que ainda não têm transação | anuncio, item, item_tag, emprestimo, foto_anuncio, transacao |
| Minha conta | Login e cadastro; seções Compras e Vendas (pagamento, envio, recebimento, avaliação e suporte; em Vendas, também os anúncios que não podem mais ser editados) e Perfil (dados, nota média e cartões). A Sacola abre em Compras | usuario, transacao, pagamento, entrega, avaliacao, suporte, anuncio, cartao |
| Painel | Análises visuais e estatísticas | todas |

## Estrutura do código

```
app.py                     # ponto de entrada: configuração da página, menu lateral e navegação
.streamlit/config.toml     # tema: cores, fontes, cantos retos e cores dos gráficos
marketplace/
├── config.py              # DATABASE_URL (.env / Secrets) e constantes do domínio
├── estilo.py              # CSS que o tema não cobre e desenho do sol
├── rotas.py               # páginas do app e seus endereços
├── menu.py                # menu lateral: páginas, sacola, conta e busca
├── navegacao.py           # acesso às páginas registradas e breadcrumb
├── erros.py               # erros da aplicação, com mensagem pronta para a tela
├── db.py                  # conexão, query_df, execute e run_tx (transações)
├── services/              # "backend": regras de negócio, permissões e todo o SQL
│   ├── anuncios.py        # anúncios, categorias, tags e busca avançada
│   ├── transacoes.py      # compra, pagamento, entrega, avaliação e suporte
│   ├── interacoes.py      # mensagens e comentários
│   ├── usuarios.py        # login, cadastro, perfil e cartões
│   ├── analises.py        # consultas do Painel
│   ├── armazenamento.py   # envio de fotos ao Supabase Storage
│   └── diagnostico.py     # conexão e tabelas visíveis
├── auth.py                # usuário logado, require_login e formulário de login/cadastro
├── components.py          # chat, comentários e card de preço
└── paginas/               # só interface: uma função pagina_* por página
    ├── loja.py            # capa, vitrine com busca e detalhe do anúncio
    ├── anunciar.py
    ├── meus_anuncios.py   # minha loja: edita e apaga anúncios sem transação
    ├── mensagens.py
    ├── conta.py           # minha conta: login e seções
    ├── transacoes.py      # seções Compras e Vendas
    ├── perfil.py          # seção Perfil
    ├── dashboard.py       # painel
    └── diagnostico.py     # ajuda quando o banco não tem as tabelas
```

As telas não têm SQL nem acessam o banco: chamam `services`, que não conhece o Streamlit.
Operações de uma transação recebem o CPF de quem as solicita e conferem a permissão no próprio serviço.

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
cp .env.example .env                                  # preencha DATABASE_URL e as chaves do Supabase
streamlit run app.py
```

Rode a partir da raiz do projeto: o tema em `.streamlit/config.toml` só é lido nessa pasta.

## Deploy (Streamlit Community Cloud)

1. O `.env` nunca vai para o GitHub: as credenciais ficam nos Secrets do app.
2. No Supabase, em *Connect*, copie a URI do **Session pooler**. A conexão direta só funciona por IPv6, que o Streamlit Cloud não usa.
3. Em share.streamlit.io: *New app* → escolha o repositório, branch `main`, arquivo `app.py`.
4. Em *Advanced settings → Secrets*, cole `DATABASE_URL`, `SUPABASE_URL` e `SUPABASE_SERVICE_KEY`:

```toml
DATABASE_URL = "postgresql://postgres.PROJETO:SENHA@HOST.pooler.supabase.com:5432/postgres"
SUPABASE_URL = "https://PROJETO.supabase.co"
SUPABASE_SERVICE_KEY = "sua-chave-de-servico"
```

Caracteres especiais da senha precisam estar codificados na URI, como no `.env`.

## Fotos dos anúncios

As fotos enviadas em Anunciar vão para o bucket público `fotos-anuncios` do Supabase Storage, e a tabela
`foto_anuncio` guarda o link. Sem `SUPABASE_URL` e `SUPABASE_SERVICE_KEY`, só é possível publicar sem fotos.
A chave de serviço dá acesso total ao projeto: use-a apenas no `.env` ou nos Secrets, nunca no código.

## Observações

- O login é apenas por e-mail (demonstração acadêmica), pois o modelo não possui senha.
- O pagamento é simulado por um botão; não há integração com gateway.