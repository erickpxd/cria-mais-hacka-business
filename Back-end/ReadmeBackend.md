# Cria Mais

Plataforma para organizar campanhas de marketing, **conferir artes automaticamente** e **aprovar com uma pessoa no controle**.

O fluxo: envia o briefing, cria o projeto, envia as artes, o sistema aponta pontos para revisar (preço, escrita, margem), a pessoa decide o que corrigir, gera versões para outros canais e um revisor aprova ou devolve. Só depois da aprovação a arte pode ser exportada.

> **Princípio do projeto:** a máquina aponta, a pessoa decide. Nenhuma alteração é aplicada sem revisão, a arte original nunca é sobrescrita e a aprovação é sempre humana.

Esta documentação cobre o **back-end** (a parte que está pronta). O front-end é descrito só no que depende dele.

---

## 1. Arquitetura

```
Navegador ──:80──► NGINX ─┬─ /      ──► front-end (React/Vite :5173)
                          └─ /api/* ──► back-end (FastAPI :80)
                                            │
                       ┌────────────────────┼────────────────────────┐
                       ▼                    ▼                        ▼
               SQLite + arquivos     PaddleOCR (no back-end)   LanguageTool (container)
               (volume ./data)       lê o texto da arte        confere a escrita
                                                                      
                                     IOPaint (container, OPCIONAL)  estende o fundo ao adaptar formatos
                                     Ollama  (container, OPCIONAL)  fora do fluxo principal
```

**Escolhas de tecnologia** (seguindo a pesquisa da equipe: IA generativa só onde for necessário):

| Necessidade | Solução | IA generativa? |
|---|---|---|
| Ler o texto das artes | PaddleOCR | Não |
| Comparar preço com o briefing | Regras + extração de dados | Não |
| Conferir ortografia | LanguageTool local | Não |
| Texto perto da borda | Geometria dos elementos | Não |
| Aplicar correções | Substituição de texto em cópia da arte | Não |
| Adaptar para outro formato | Outpainting (IOPaint), opcional | Sim (modelo LaMa), controlado |

---

## 2. Estrutura de pastas

```
projeto/
├── docker-compose.yaml         # Orquestra todos os serviços (com profiles opcionais)
├── nginx.conf                  # Porta de entrada: separa / (front) e /api (back-end)
├── .env.example                # Variáveis do compose (copie para .env)
├── .gitignore
├── README.md
│
├── Back-end/
│   ├── Dockerfile
│   ├── requirements.txt        # Dependências leves (API, banco, imagens, PDF/DOCX)
│   ├── requirements-ocr.txt    # Dependências do PaddlePaddle/PaddleOCR
│   ├── app/
│       ├── main.py             # Cria o app, CORS, rotas, tratamento de erros, /api/saude
│       ├── config.py           # TODOS os parâmetros (limites, URLs, regras)
│       ├── db.py               # Conexão SQLAlchemy e criação das tabelas
│       ├── models.py           # Tabelas: Projeto, Arte, VersaoArte, Analise, Achado...
│       ├── schemas.py          # Modelos do módulo opcional de visão (llava)
│       ├── serializers.py      # Objeto do banco -> JSON que o front consome
│       ├── deps.py             # Usuário atual (X-Usuario) e checagem de revisor
│       │
│       ├── routes/             # Camada HTTP: só orquestra, sem regra pesada
│       │   ├── projects.py     # Dashboard, projetos, briefing (extrair, anexar, baixar)
│       │   ├── arts.py         # Upload, versões, análise, correções, adaptação, comentários
│       │   ├── images.py       # Análise e leitura de imagens
│       │   └── approvals.py    # Abas, avaliação, aprovar, devolver, exportar
│       │
│       └── services/           # Regras de negócio e integrações
│           ├── briefing.py     # Lê PDF/DOCX/TXT e extrai os campos (com a página)
│           ├── ocr.py          # Interface do OCR (PaddleOCR por trás)
│           ├── ortografia.py   # Cliente do LanguageTool
│           ├── analyses.py     # As conferências automáticas
│           ├── corrections.py  # Aplica correções aceitas numa CÓPIA da arte
│           ├── outpainting.py  # Estende o fundo via IOPaint (código do outro dev, corrigido)
│           ├── adaptations.py  # Leva a arte ao formato do canal (usa o outpainting)
│           ├── formatos.py     # Tabela de canais e tamanhos
│           ├── armazenamento.py# Arquivos em disco, com proteção de caminho
│           ├── erros.py        # ErroNegocio / ErroServicoIA (status HTTP + mensagem)
│           └── vision.py       # OPCIONAL: llava via Ollama (fora do fluxo principal)
│
├── iopaint/
│   └── Dockerfile              # Imagem do IOPaint (não existe oficial no Docker Hub)
│
│   ── Pastas que existem no repositório mas NÃO fazem parte desta entrega ──
├── Front-end/                  # React (Dockerfile.dev, app/). Ainda aponta para as rotas antigas
├── Agentes/                    # Volumes de modelos, criados em tempo de execução:
│   ├── ollama-models/          #   (só com --profile ia)
│   ├── iopaint-models/         #   modelo LaMa baixado na 1ª execução
│   └── paddle-cache/           #   modelos do PaddleOCR baixados na 1ª leitura
└── data/                       # Criada em tempo de execução: banco SQLite, briefings, versões das artes
```

> **Atenção:** se existir uma pasta `IOPaint/` (com maiúsculas) ao lado de `iopaint/`, ela é duplicada e deve ser removida. No Windows e no macOS as duas colidem.
> A pasta `.devcontainer/`, se existir, aponta para um Dockerfile que não existe e pode ser apagada.

### Como as camadas se relacionam

```
routes/  ──chama──►  services/  ──usa──►  models/db
   │                     │
   └─ HTTP e validação   └─ regras, OCR, IA, arquivos
```

Regra de ouro: **rotas não contêm regra de negócio**. Para mudar uma conferência, mexa em `app/services/analyses.py`. Para trocar de OCR, em `app/services/ocr.py`.

---

## 3. Como rodar

Requisito: Docker.

```bash
# 1) Subida padrão (back-end, LanguageTool, front, nginx)
docker compose up -d --build

# 2) Com outpainting real (IOPaint)
echo "OUTPAINTING_ATIVO=true" > .env
docker compose --profile outpainting up -d --build

# 3) Com Ollama (experimentos com llava; fora do fluxo principal)
docker compose --profile ia up -d
```

| O quê | Endereço |
|---|---|
| Aplicação (via Nginx) | http://localhost |
| Documentação interativa da API (Swagger) | http://localhost:3000/docs |
| Estado dos serviços de apoio | http://localhost:3000/api/saude |

A porta 3000 existe só para testar a API. O front fala com o back-end pelo Nginx (`/api`).

**Hot reload:** use `docker compose watch` (ou `up --watch`). Com `up -d` puro, o código não é sincronizado.

**O primeiro build é demorado** (PaddlePaddle é grande) e a primeira leitura de OCR baixa os modelos para `Agentes/paddle-cache`. A primeira subida do IOPaint também baixa o modelo LaMa.

### Validação local

O backend deve ser validado em três etapas: sintaxe, configuração do Compose e
endpoints HTTP. Execute os comandos a partir da raiz do repositório:

```bash
# 1) Sintaxe Python
python3 -m compileall -q Back-end/app

# 2) Configuração resolvida do Compose
docker compose config

# 3) Subida da aplicação e dos serviços
docker compose up -d --build

# 4) Smoke tests da API
curl -fsS http://localhost:3000/api
curl -fsS http://localhost:3000/api/saude
curl -fsS -H "X-Usuario: ana" http://localhost:3000/api/me
curl -fsS -H "X-Usuario: ana" http://localhost:3000/api/formatos

# 5) Estado dos containers
docker compose ps
```

O resultado esperado de `/api` é `{"status":"ok"}`. Em `/api/saude`, `api` e
`languagetool` devem estar como `true`. Um usuário inválido deve retornar HTTP
401. Para acompanhar erros de inicialização:

```bash
docker compose logs --tail=200 back-end languagetool
```

### Cache e rebuild

O projeto usa dois tipos de persistência que não devem ser apagados durante uma
subida normal:

- `./data:/data`: banco SQLite, briefings e versões das artes;
- `./Agentes/paddle-cache:/root/.paddlex`: modelos baixados pelo PaddleOCR.

O `docker compose watch` sincroniza `Back-end/app` e refaz a imagem quando
`requirements.txt` ou `requirements-ocr.txt` muda. Alterações apenas no código
não exigem `--no-cache`. Use rebuild sem cache somente para diagnosticar uma
imagem realmente inconsistente:

```bash
docker compose build --no-cache back-end
docker compose up -d back-end
```

Não use `docker compose down -v` para corrigir problemas comuns: a opção `-v`
remove volumes gerenciados pelo Compose. Os diretórios `data/` e
`Agentes/paddle-cache/` são bind mounts e devem ser preservados.

---

## 4. Configuração

Tudo está em `Back-end/app/config.py`. Qualquer valor pode ser sobrescrito por variável de ambiente (no `docker-compose.yml` ou num `.env`).

| Variável | Padrão | Para quê |
|---|---|---|
| `DATABASE_URL` | `sqlite:////data/cria_mais.db` | Banco. Para Postgres, basta trocar a URL |
| `DATA_DIR` | `/data` | Onde ficam briefings e versões das artes |
| `OCR_MOTOR` / `OCR_LANG` | `paddle` / `latin` | Motor e idioma do OCR (confirmar no 1º teste real) |
| `OCR_CONFIANCA_MIN` | `0.6` | Descarta leituras do OCR abaixo disso |
| `MIN_LARGURA` / `MIN_ALTURA` | `320` / `320` | Resolução mínima para análise simples de imagens |
| `MIN_NITIDEZ` | `20.0` | Nitidez mínima para análise simples de imagens |
| `CRITERIOS_VISAO` | lista padrão | Critérios enviados ao modelo Ollama opcional |
| `LANGUAGETOOL_URL` | `http://languagetool:8010` | Corretor ortográfico local |
| `ORTOGRAFIA_IGNORAR` | `[]` | Marcas/termos que não devem ser "corrigidos" (formato JSON) |
| `MARGEM_MINIMA_PCT` | `0.04` | Distância mínima do texto à borda (% do menor lado) |
| `OUTPAINTING_ATIVO` | `false` | Liga o IOPaint real. Desligado usa borda replicada |
| `IOPAINT_URL` | `http://iopaint:8080` | Endereço do IOPaint |
| `OUTPAINTING_MAX_EXTENSAO` | `1.0` | Máximo de imagem nova gerada (1.0 = +100%) |
| `MAX_BRIEFING_MB` / `MAX_ARTE_MB` | `20` | Limites de upload |

Os formatos de publicação estão em `app/services/formatos.py`. **Feed (1080×1080) e Stories (1080×1920) vêm do design. WhatsApp e Banner do site estão com tamanhos provisórios** (o design só diz "modelo configurável" e "conforme o briefing") e precisam ser confirmados.

---

## 5. Modelo de dados

```
Projeto ──< Arte ──< VersaoArte ──1 Analise ──< Achado
              ├──< Comentario
              └──< Aprovacao
EventoDecisao   (registro de toda decisão humana)
```

- **VersaoArte**: a **v1 é sempre a original e nunca é alterada**. Correções e adaptações criam versões novas, com `origem` (`upload`, `correcao`, `adaptacao`) e uma nota.
- **Achado**: um ponto para revisar, com região, sugestão de/para e a decisão da pessoa (`pendente`, `aceito`, `rejeitado`).
- **Aprovacao**: guarda a **versão** que o revisor viu. A exportação entrega exatamente essa.
- **EventoDecisao**: base para um futuro ML clássico (a pesquisa recomenda registrar decisões humanas desde o primeiro dia).

---

## 6. Fluxo e status da arte

```
upload ─► em_analise ─┬─► precisa_ajustes   (há achados pendentes)
                      └─► em_producao       (nada a revisar)

precisa_ajustes ──(pessoa decide as sugestões)──► em_producao
em_producao ──(enviar)──► aguardando_aprovacao ─┬─► aprovada
                                                └─► precisa_ajustes (devolvida)
```

### As conferências automáticas

1. **Preço**: o preço do briefing precisa aparecer na arte. Só gera achado se **não aparecer em lugar nenhum** (evita falso alarme com preço "de/por").
2. **Ortografia**: LanguageTool local. Considera só erros de escrita e ignora palavras do próprio briefing (produto, marca).
3. **Margem**: texto a menos de 4% do menor lado da borda.

Quando uma verificação **não consegue rodar** ou **não tem como confirmar** (prazo ausente, serviço fora do ar), isso vira uma nota ("Prazo: Não foi possível confirmar"), nunca um "tudo certo" falso.

### Adaptação de formato

Cria **uma nova arte por canal**, a original não muda. O outpainting estende só uma dimensão, sem cortar nem reduzir, e depois **cola a original de volta por cima**, garantindo que nenhum pixel dela foi alterado. Acima de +100% de imagem nova, recusa e pede ajuste manual.

---

## 7. Endpoints

Todas as rotas começam com `/api`. O usuário é informado pelo header `X-Usuario`.

**Início e projetos**

| Método | Rota | Função |
|---|---|---|
| GET | `/me` | Usuário atual e contagem do selo de Aprovações |
| GET | `/formatos` | Canais e tamanhos |
| GET | `/dashboard` | Cards de atenção e projetos recentes |
| GET | `/projetos`, `/projetos/{id}` | Lista e detalhe (filtros `status`, `canal`) |
| POST | `/briefings/extrair` | Lê o briefing e devolve os campos com a página |
| POST | `/projetos` | Cria o projeto (aceita `briefing_token`) |
| GET | `/projetos/{id}/briefing` | Baixa o briefing original |

**Artes**

| Método | Rota | Função |
|---|---|---|
| POST | `/projetos/{id}/artes` | Envia a arte e dispara a conferência |
| POST | `/artes/{id}/versoes` | Envia nova versão (após devolução) |
| GET | `/artes/{id}` | Detalhe, versões e análise (`conferindo` indica andamento) |
| GET | `/artes/{id}/analise` | Achados da versão atual |
| GET | `/artes/{id}/versoes/{n}/imagem` | Imagem de uma versão |
| POST | `/artes/{id}/correcoes` | Aceita/rejeita sugestões; as aceitas geram nova versão |
| POST | `/artes/{id}/enviar-aprovacao` | Envia para a revisão |
| POST | `/artes/{id}/adaptar` | Gera a arte em outros canais |
| GET/POST | `/artes/{id}/comentarios` | Comentários por região |

**Aprovações**

| Método | Rota | Função |
|---|---|---|
| GET | `/aprovacoes?aba=pendentes\|aprovadas\|devolvidas` | Listas com contagens |
| GET | `/aprovacoes/{arte_id}` | Tudo da tela "Avaliar arte" |
| POST | `/artes/{id}/aprovar` | Aprova (só revisor, nunca a própria arte) |
| POST | `/artes/{id}/solicitar-ajustes` | Devolve ao criador com comentário |
| GET | `/artes/{id}/exportar` | Baixa a versão aprovada (403 antes da aprovação) |

**Sistema:** `GET /api` e `GET /api/saude` (estado do LanguageTool, IOPaint e configuração do OCR).
O endpoint `/api/saude` é único; a rota antiga de saúde da análise Ollama foi removida para evitar contratos conflitantes.

Erros sempre voltam como `{"detail": "mensagem pronta para exibir"}`.

## 7.1 Integração com o front-end

Esta seção é o contrato de integração para quem estiver implementando o front-end.
O front-end deve consumir somente os caminhos `/api/*`; não deve acessar diretamente
o hostname interno `back-end`.

### URLs

| Ambiente | Base da API |
|---|---|
| Desenvolvimento pelo Nginx | `http://localhost/api` |
| Backend direto para diagnóstico | `http://localhost:3000/api` |
| Dentro da rede Docker | `http://back-end:80/api` |

Em desenvolvimento no navegador, prefira sempre URLs relativas:

```ts
fetch("/api/projetos")
```

Isso mantém o mesmo código funcionando atrás do Nginx e evita configurar uma URL
interna do Docker no browser.

### Headers

Todas as rotas que dependem de usuário aceitam o usuário de demonstração no header:

```http
X-Usuario: ana
```

Usuários disponíveis:

```text
ana     designer
bruno   designer
rafael  revisor
```

O header deve ser enviado em todas as requisições autenticadas. Se ele não for
enviado, o backend usa `ana` como padrão. Um usuário desconhecido retorna `401`.

Não defina manualmente `Content-Type` ao enviar `FormData`; o navegador precisa
gerar o boundary multipart:

```ts
const form = new FormData();
form.append("file", file);

await fetch("/api/projetos/1/artes?canal=instagram_feed", {
  method: "POST",
  headers: { "X-Usuario": "ana" },
  body: form,
});
```

### Fluxo recomendado da tela

1. Consulte `GET /api/me` e `GET /api/formatos` ao carregar a aplicação.
2. Envie o briefing com `POST /api/briefings/extrair`.
3. Mostre os campos retornados e envie o `token` em `POST /api/projetos`.
4. Envie cada arte com `POST /api/projetos/{id}/artes?canal={canal}`.
5. Consulte `GET /api/artes/{id}` até a análise deixar de estar pendente.
6. Mostre os achados retornados em `analise.achados`.
7. Envie decisões para `POST /api/artes/{id}/correcoes`.
8. Quando a arte estiver pronta, use `POST /api/artes/{id}/enviar-aprovacao`.
9. A tela de revisão usa `GET /api/aprovacoes` e `GET /api/aprovacoes/{id}`.
10. Depois da aprovação, baixe `GET /api/artes/{id}/exportar`.

### Upload de briefing

```http
POST /api/briefings/extrair
Content-Type: multipart/form-data
X-Usuario: ana
```

Campo multipart obrigatório: `file`.

Extensões aceitas: `.pdf`, `.docx`, `.txt`. A resposta contém:

```json
{
  "token": "token-hexadecimal",
  "arquivo": "briefing.pdf",
  "total_paginas": 2,
  "campos": {},
  "avisos": []
}
```

O token é temporário e deve ser enviado sem alteração no campo
`briefing_token` da criação do projeto.

### Criação de projeto

```http
POST /api/projetos
Content-Type: application/json
X-Usuario: ana
```

Exemplo:

```json
{
  "nome": "Campanha de verão",
  "objetivo": "Divulgar o produto",
  "descricao": "Campanha para redes sociais",
  "prazo": "2026-12-20",
  "produto": "Produto X",
  "preco": "17,90",
  "informacoes_obrigatorias": "Compre agora",
  "orientacoes": "Usar identidade visual oficial",
  "canais": ["instagram_feed", "instagram_stories"],
  "briefing_token": "token-hexadecimal"
}
```

O campo `canais` deve usar os slugs devolvidos por `GET /api/formatos`.

### Upload e análise de arte

```http
POST /api/projetos/{projeto_id}/artes?canal=instagram_feed
Content-Type: multipart/form-data
X-Usuario: ana
```

Campo multipart obrigatório: `file`.

A resposta inicial contém `status: "em_analise"`. A análise é executada em
background; o frontend deve consultar `GET /api/artes/{arte_id}` em vez de
assumir que ela terminou na resposta do upload.

Estados possíveis da arte:

```text
em_analise
em_producao
precisa_ajustes
aguardando_aprovacao
aprovada
```

Estados possíveis da análise:

```text
concluida
erro
```

### Achados e correções

Os achados ficam em `analise.achados`. Cada achado pode conter:

```json
{
  "id": 10,
  "tipo": "erro_escrita",
  "regiao": { "x": 10, "y": 20, "w": 100, "h": 30 },
  "sugestao": {
    "linha_original": "Texto incorreto",
    "linha_corrigida": "Texto corrigido"
  },
  "decisao": "pendente"
}
```

Para aceitar ou rejeitar sugestões:

```http
POST /api/artes/{arte_id}/correcoes
Content-Type: application/json
X-Usuario: ana
```

```json
{
  "aceitos": [10, 11],
  "rejeitados": [12]
}
```

Somente achados aceitos que tenham `sugestao.linha_corrigida` geram uma nova
versão. A versão original nunca é sobrescrita.

### Imagens e versões

Use o campo `imagem_url` retornado pelo backend. Ele é relativo à mesma origem:

```ts
const url = `${apiBase}${arte.imagem_url}`;
```

Se `apiBase` for vazio e o navegador estiver usando o Nginx, basta usar:

```tsx
<img src={arte.imagem_url} alt={arte.nome} />
```

Não monte caminhos de arquivos do volume `/data` no frontend. Arquivos só devem
ser acessados pelas rotas HTTP:

```text
GET /api/artes/{id}/versoes/{numero}/imagem
GET /api/projetos/{id}/briefing
GET /api/artes/{id}/exportar
```

### Aprovação

Somente `rafael` pode aprovar ou devolver uma arte. O frontend deve esconder ou
desabilitar os botões de decisão para designers, mas o backend continua sendo a
autoridade e retorna `403` quando necessário.

Antes da aprovação, a arte deve estar em `aguardando_aprovacao`. Depois de
aprovada, a exportação fica liberada. Uma aprovação não deve ser simulada no
frontend; sempre aguarde a resposta do backend.

### Polling da análise

Como a análise usa uma tarefa em background, o frontend pode consultar o detalhe
com um intervalo curto, por exemplo 2 segundos, enquanto `status` for
`em_analise`. Interrompa o polling quando o estado for `em_producao`,
`precisa_ajustes` ou `erro`.

Não faça polling infinito e não inicie uma nova análise apenas para atualizar a
tela. O upload já dispara a análise automaticamente.

### Erros

Todas as respostas de erro de negócio usam:

```json
{
  "detail": "Mensagem pronta para exibir"
}
```

O frontend deve tratar pelo menos estes status:

| Status | Significado |
|---:|---|
| `400` | Arquivo ou dados inválidos |
| `401` | Usuário desconhecido |
| `403` | Usuário sem permissão ou exportação ainda bloqueada |
| `404` | Projeto, arte ou arquivo não encontrado |
| `409` | Operação incompatível com o estado atual |
| `413` | Arquivo acima do limite |
| `415` | Tipo de arquivo não aceito |
| `422` | Campo ou canal inválido |
| `503`/`504` | Serviço auxiliar indisponível ou lento |

### Proxy do Nginx

O Nginx encaminha `/api` para o serviço `back-end` e `/` para o serviço
`front-end`. O frontend não deve usar `localhost:3000` quando estiver sendo
servido pelo Nginx em `http://localhost`; use `/api`.

### Regra para mudanças de contrato

Se o frontend precisar de um campo novo, primeiro confirme se ele já está no
serializer correspondente. Não dependa de atributos internos do SQLAlchemy nem
de caminhos do filesystem. Alterações de payload, status ou rota devem ser
documentadas neste arquivo antes de serem consumidas pela interface.

### Usuários de demonstração

| Header `X-Usuario` | Pessoa | Papel |
|---|---|---|
| `ana` | Ana Costa | designer |
| `bruno` | Bruno Lima | designer |
| `rafael` | Rafael Martins | revisor |

---

## 8. Como estender

**Adicionar uma nova conferência** (ex.: cor fora do padrão):
1. Crie a regra em `app/services/analyses.py` e adicione os achados com um novo `tipo`.
2. Inclua o nome em `verificacoes_aplicadas`.
3. Se tiver correção automática, preencha `sugestao.linha_corrigida`.

**Trocar o OCR:** implemente a interface `MotorOCR` em `app/services/ocr.py` (um método `ler(imagem)` que devolve linhas com texto e caixa) e ajuste `obter_motor()`.

**Novo formato de publicação:** adicione em `app/services/formatos.py`.

---

## 9. Limitações conhecidas

- **PaddleOCR real ainda não foi executado.** O adaptador segue o formato documentado da v3, mas o primeiro teste real pode pedir ajustes (idioma, versão).
- **Tarefas em segundo plano não são duráveis.** Se o servidor reiniciar durante uma conferência, a arte fica em `em_analise`. Para produção, usar uma fila (Celery, RQ ou similar).
- **A leitura do briefing é heurística** (rótulos em maiúsculas ou "Rótulo: valor").
- **A correção de texto funciona bem em fundo liso.** Em foto ou degradê forte pode ficar visível, por isso toda versão corrigida passa por revisão.
- **A adaptação não reorganiza a composição**, só estende o fundo. Rearranjar elementos exige artes com layout editável.
- **Cor fora do padrão não foi implementada** (a identidade oficial não foi fornecida).
- **Login é de demonstração**, sem autenticação real.
- **Arquivos temporários de briefing** (`data/tmp/`) não são limpos automaticamente.
- **O front-end ainda aponta para as rotas antigas** e precisa ser ajustado a esta API.