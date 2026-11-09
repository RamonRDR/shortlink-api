# ShortLink API

[English (versão principal)](README.md) | **Português (Brasil)** | [Español](README.es.md)

[![CI](https://github.com/RamonRDR/shortlink-api/actions/workflows/ci.yml/badge.svg)](https://github.com/RamonRDR/shortlink-api/actions/workflows/ci.yml)

Encurtador de URLs com API REST, **Python 3.14, FastAPI, SQLAlchemy, Alembic e
PostgreSQL**. Projeto de portfólio backend que demonstra design de APIs, integridade
transacional, concorrência, testes automatizados e práticas de segurança.

**Público-alvo:** recrutadores de backend, Python, automação e engenharia de software.
O `README.md` em inglês é a documentação principal; esta versão mantém
equivalência de recursos, limitações e instruções de execução.

## Funcionalidades

- Criar códigos aleatórios únicos ou aliases personalizados (201; conflito 409).
- Redirecionar publicamente com HTTP 302; links expirados/desativados retornam 404.
- Consultar, listar com paginação/filtro, alterar e excluir logicamente links.
- Visualizar total de acessos, agregados diários UTC e links mais acessados.
- Autenticar rotas administrativas por API key com comparação em tempo constante.
- Limitar requisições administrativas por processo e validar URLs HTTP/HTTPS.
- Documentação OpenAPI em /docs; verificação do banco em /health.
- Migrações Alembic, testes PostgreSQL e CI com GitHub Actions.

## Estrutura do projeto

| Caminho | Responsabilidade |
| --- | --- |
| `src/shortlink/main.py` | Rotas, injeção de dependências e respostas HTTP |
| `src/shortlink/schemas.py` | Contratos de entrada e saída validados |
| `src/shortlink/services.py` | Regras de negócio dos links e códigos curtos |
| `src/shortlink/repositories.py` | Consultas SQLAlchemy e atualizações atômicas |
| `src/shortlink/analytics.py` | Relatórios agregados |
| `src/shortlink/security.py`, `rate_limit.py` | Autenticação administrativa e limitação de taxa |
| `migrations/` | Versionamento do banco com Alembic |
| `tests/` | Testes com PostgreSQL descartável |
| `.github/workflows/ci.yml` | Verificações automáticas no GitHub Actions |

## Arquitetura

    Cliente -> FastAPI -> Pydantic / API key / limite de taxa
                             |
                        serviços de negócio
                             |
                         SQLAlchemy
                             |
                         PostgreSQL
                       links + daily_clicks

    Navegador -> GET /{code} -> atualização atômica -> HTTP 302

Não utiliza Redis, filas ou sistema de cadastro de usuários. As escolhas
estão descritas nas [decisões técnicas](docs/decisions.md).

## Instalação e configuração

Requisitos: Python **3.14**, PostgreSQL **16** ou Docker com Compose.

**Docker Compose:**

    cp .env.example .env
    # Edite .env: defina POSTGRES_PASSWORD forte e
    # SHORTLINK_ADMIN_API_KEY aleatória com no mínimo 32 caracteres.
    docker compose up --build -d
    curl http://localhost:8000/health

O Compose aguarda o banco e executa migrações automaticamente. Não use
credenciais de exemplo em produção. O arquivo .env está ignorado pelo Git.

**Execução local:**

Configure PostgreSQL e as variáveis:

| Variável | Descrição |
| --- | --- |
| SHORTLINK_DATABASE_URL | postgresql+psycopg://usuario:senha@localhost:5432/shortlink |
| SHORTLINK_ADMIN_API_KEY | Segredo aleatório, mínimo de 32 caracteres |
| SHORTLINK_BASE_URL | URL pública, por exemplo http://localhost:8000 |
| SHORTLINK_MAX_REQUESTS_PER_MINUTE | Limite administrativo por processo; padrão 60 |

    python3.14 -m venv .venv
    . .venv/bin/activate
    pip install -e ".[dev]"
    alembic upgrade head
    uvicorn shortlink.main:app --reload

No PowerShell, a ativação é .venv\Scripts\Activate.ps1.

## Referência dos endpoints

As rotas públicas incluem `GET /{code}`, `GET /health`, `GET /docs` e
`GET /openapi.json`. As rotas de administração e analytics sob
`/api/v1` exigem o cabeçalho `X-API-Key`.

| Método | Endpoint | Finalidade |
| --- | --- | --- |
| `POST` | `/api/v1/links` | Criar link curto ou alias personalizado |
| `GET` | `/api/v1/links` | Listar com `limit`, `offset` e filtro opcional `active` |
| `GET` | `/api/v1/links/{code}` | Consultar detalhes administrativos |
| `PATCH` | `/api/v1/links/{code}` | Alterar status ativo ou expiração |
| `DELETE` | `/api/v1/links/{code}` | Excluir logicamente um link (`204`) |
| `GET` | `/api/v1/links/{code}/analytics` | Total e histórico diário UTC (`days`) |
| `GET` | `/api/v1/analytics` | Total de links, acessos e links populares (`top`) |
| `GET` | `/{code}` | Redirecionamento público HTTP `302` |
| `GET` | `/health` | Verificar disponibilidade do banco |
| `GET` | `/docs` | Documentação OpenAPI interativa |

## Exemplos de requisições e respostas

Substitua YOUR_ADMIN_KEY pela chave configurada.

**Criar link (201):**

    curl -X POST http://localhost:8000/api/v1/links \
      -H "X-API-Key: YOUR_ADMIN_KEY" \
      -H "Content-Type: application/json" \
      -d '{"target_url":"https://example.org/docs","alias":"my-docs"}'

Exemplo ilustrativo de resposta (datas fictícias):

    {
      "code": "my-docs",
      "target_url": "https://example.org/docs",
      "short_url": "http://localhost:8000/my-docs",
      "is_active": true,
      "expires_at": null,
      "created_at": "2026-11-07T12:00:00Z",
      "updated_at": "2026-11-07T12:00:00Z",
      "click_count": 0,
      "last_accessed_at": null
    }

**Redirecionar (302):**

    curl -i http://localhost:8000/my-docs

A resposta inclui o cabeçalho Location; somente GET é suportado, não HEAD.

**Administrar links e analytics (exige X-API-Key):**

    curl -H "X-API-Key: YOUR_ADMIN_KEY" 'http://localhost:8000/api/v1/links?limit=20&offset=0'
    curl -H "X-API-Key: YOUR_ADMIN_KEY" http://localhost:8000/api/v1/links/my-docs
    curl -X PATCH -H "X-API-Key: YOUR_ADMIN_KEY" \
      -H "Content-Type: application/json" -d '{"is_active":false}' \
      http://localhost:8000/api/v1/links/my-docs
    curl -X DELETE -H "X-API-Key: YOUR_ADMIN_KEY" http://localhost:8000/api/v1/links/my-docs
    curl -H "X-API-Key: YOUR_ADMIN_KEY" 'http://localhost:8000/api/v1/links/my-docs/analytics?days=30'
    curl -H "X-API-Key: YOUR_ADMIN_KEY" 'http://localhost:8000/api/v1/analytics?top=10'

O contrato completo de entrada/saída, erros HTTP e exemplos interativos
estão disponíveis em http://localhost:8000/docs. Falhas de autenticação
retornam 401; excesso de requisições retorna 429 com Retry-After.

## Analytics e privacidade

Contagens representam redirecionamentos processados, não a confirmação
de carregamento do destino. Agregação diária utiliza UTC. Não são
armazenados IPs, agentes de usuário nem referrers pela aplicação. O Docker e
Compose desativam por padrão os logs HTTP do Uvicorn; proxies reversos e a
hospedagem podem registrar requisições e precisam de configuração própria.
Transações PostgreSQL mantêm contadores consistentes sob concorrência.

## Testes e CI

Com banco de testes isolado (nome terminado em _test) e variáveis configuradas:

    ruff check .
    ruff format --check .
    mypy src/shortlink
    alembic upgrade head
    pytest
    python -m build --wheel
    docker build .

O GitHub Actions executa Ruff lint/format, mypy, migrações e verificação de
drift do Alembic, testes de integração PostgreSQL, build de wheel Python e
imagem Docker em PRs direcionados à `main` e pushes na `main`. São usados
runners hospedados e credenciais temporárias, sem deploy ou publicação.

## Segurança e limitações

Apenas administradores criam e alteram links. Não ocorre busca do destino
pelo servidor. São rejeitados esquemas inseguros, IPs privados e hosts locais,
mas não há verificação de reputação dos domínios nem garantia contra phishing.
Não é apropriado oferecer cadastro anônimo sem proteções adicionais.

Limitações: chave administrativa compartilhada; rate limiting em memória
por processo, sem distribuição entre réplicas; sem rastreamento de visitantes
únicos, limpeza programada, tracing externo ou deploy automático. Códigos excluídos permanecem
reservados. Consulte [decisões técnicas](docs/decisions.md).

## Licença

[MIT](LICENSE), Copyright (c) 2026 Ramon Rodriguez.
