# Cria Mais — POC funcional

O Cria Mais organiza briefings, artes, versões e aprovação humana em uma demonstração persistente. O login é propositalmente mockado no frontend; todo o restante do fluxo principal usa a API e o banco local.

## O que funciona

- Personas demo: Ana (Criador) e Rafael (Revisor), alternáveis pela interface.
- Projeto e briefing manual persistidos em SQLite.
- Extração determinística de PDF, DOCX e TXT, incluindo tabelas DOCX e OCR de páginas escaneadas, com campos ausentes e conflitos explícitos.
- Upload real de PNG/JPG, original imutável e novas versões vinculadas.
- OCR local com preço, ortografia e margem, usando estados `queued`, `processing`, `completed` e `failed`.
- Geração por template editável em Feed, Stories, WhatsApp e Banner.
- Prévia lado a lado e criação de nova versão ao editar campos do template.
- Submissão, devolução com comentário obrigatório, aprovação humana e exportação da versão aprovada.
- Histórico de versões e decisões.

Correção automática de bitmaps arbitrários e adaptação por outpainting não são apresentadas como prontas: essas rotas retornam `501`. O caminho confiável da POC é o template estruturado.

## Executar

Pré-requisito: Docker com Compose.

```bash
docker compose up -d --build
```

Acessos:

- Aplicação: <http://localhost>
- OpenAPI: <http://localhost:3000/docs>
- Saúde básica: <http://localhost:3000/health>
- Dependências: <http://localhost:3000/api/v1/health/dependencies>

Para parar os containers sem apagar dados:

```bash
docker compose down
```

Os dados ficam em `./data`, ignorado pelo Git.

## Desenvolvimento e validação

Frontend:

```bash
cd Front-end/app
npm install
npm run lint
npm run build
npm run test:e2e
npm audit --omit=dev
```

Backend pela mesma imagem da aplicação:

```bash
docker compose run --rm --no-deps \
  -v "$PWD/Back-end:/code" back-end \
  sh -c 'pip install -q -r requirements-dev.txt && ruff check app tests migrations && pytest -q'
```

As migrations rodam automaticamente antes do Uvicorn. Manualmente:

```bash
docker compose run --rm back-end alembic upgrade head
```

Para validar a implantação com PostgreSQL em vez de SQLite:

```bash
POSTGRES_PASSWORD='troque-esta-senha' \
docker compose -f docker-compose.yaml -f docker-compose.postgres.yaml up -d --build
```

## Arquitetura

```text
Browser → Nginx → React/Vite
              └→ FastAPI /api/v1
                    ├→ SQLite + storage local
                    ├→ PaddleOCR local
                    └→ LanguageTool local
```

Ollama e IOPaint permanecem opcionais e fora do fluxo demonstrável principal. Não são necessários para subir a POC.

## Limites

- `X-Demo-User` seleciona uma persona fictícia; não é autenticação de produção.
- `BackgroundTasks` não é uma fila durável.
- SQLite e armazenamento local servem somente à demonstração controlada.
- O resultado automático auxilia a pessoa revisora e não representa aprovação regulatória.
- Não existe publicação automática nem acesso presumido a dados corporativos.

O diagnóstico detalhado está em [`docs/POC_BACKEND_IMPLEMENTACAO.md`](docs/POC_BACKEND_IMPLEMENTACAO.md), e o escopo original em [`PLANO_BACKEND_CRIAMAIS.md`](PLANO_BACKEND_CRIAMAIS.md).
