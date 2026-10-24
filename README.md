# Hackton Avanade - Análise inteligente de imagens

Aplicação desenvolvida para o desafio Pague Menos. O sistema recebe uma imagem,
faz uma validação técnica local e, quando a imagem atende aos requisitos básicos,
encaminha o arquivo para um modelo de visão executado pelo Ollama. O resultado
informa se a imagem foi aprovada, em qual etapa ocorreu a decisão e os motivos
da reprovação, quando aplicável.

## O que foi modificado

### Backend

- Migração da API para **FastAPI**, com execução assíncrona.
- Criação de um fluxo de análise em duas etapas:
  1. validação técnica rápida, usando OpenCV;
  2. análise semântica da imagem por um modelo de visão no Ollama.
- Validações de entrada antes do processamento:
  - tipo MIME da imagem;
  - tamanho máximo do arquivo;
  - arquivo vazio;
  - imagem inválida ou impossível de decodificar.
- Validação de critérios técnicos, como:
  - resolução mínima;
  - proporção esperada;
  - nitidez mínima.
- Uso de `asyncio.to_thread` para executar as operações de CPU do OpenCV
  sem bloquear o servidor assíncrono.
- Definição de schemas de resposta com Pydantic.
- Tratamento explícito de falhas de comunicação com o Ollama, incluindo:
  - timeout;
  - modelo ainda não baixado;
  - indisponibilidade do serviço;
  - resposta fora do formato JSON esperado.
- Inclusão de endpoint de saúde para verificar o Ollama e a disponibilidade
  do modelo de visão.
- Manutenção de um endpoint separado para extração de texto manuscrito por OCR.

### Frontend

- Aplicação criada com **React, TypeScript e Vite**.
- Componente de seleção de imagem com:
  - seletor de arquivos nativo;
  - filtro para arquivos de imagem;
  - pré-visualização local antes do envio;
  - callback para integração com a API.
- Estrutura inicial para seleção de idioma.
- Comunicação com o backend por meio do caminho `/api`, encaminhado pelo Nginx.
- Configuração de desenvolvimento com atualização automática dos arquivos
  usando o recurso `develop.watch` do Docker Compose.

### Infraestrutura e execução

- Conteinerização do frontend e do backend.
- Inclusão do Ollama como serviço independente.
- Download automático do modelo de visão na inicialização da stack.
- Inclusão do Nginx como proxy reverso:
  - `/` encaminha para o frontend;
  - `/api` encaminha para o backend.
- Rede Docker compartilhada entre os serviços.
- Possibilidade de habilitar GPU NVIDIA no serviço do Ollama, quando disponível.

## Arquitetura

```text
Navegador
   |
   v
Nginx (porta 80)
   |------------------------------|
   v                              v
Frontend React/Vite          Backend FastAPI (porta 3000)
                                  |
                                  v
                           Ollama (porta 11434)
                                  |
                                  v
                           Modelo de visão
```

O frontend é servido pelo Vite dentro do container. O Nginx centraliza o acesso
da aplicação e evita que o navegador precise conhecer diretamente as portas
internas do frontend e do backend.

## Fluxo de análise

1. O usuário seleciona uma imagem no frontend.
2. O componente de upload cria uma prévia local e envia o arquivo para a API.
3. O backend valida o tipo, o tamanho e o conteúdo do arquivo.
4. O OpenCV decodifica a imagem e executa as verificações técnicas.
5. Se algum critério técnico falhar, a imagem é reprovada sem consumir o modelo
   de visão.
6. Se a imagem passar na etapa técnica, o backend envia o arquivo ao Ollama.
7. O modelo avalia os critérios configurados e retorna um JSON estruturado.
8. O backend valida a resposta do modelo e devolve o resultado ao frontend.

Essa separação reduz o custo das análises e facilita a identificação da causa
de uma reprovação.

## API

### `POST /api/analisar`

Recebe uma imagem no campo multipart `file`.

Possíveis resultados:

- `200`: análise concluída;
- `400`: arquivo vazio, inválido ou que não representa uma imagem;
- `413`: arquivo acima do limite configurado;
- `415`: tipo de arquivo não aceito;
- `502`, `503` ou `504`: falha na comunicação ou na resposta do Ollama.

O retorno inclui o nome do arquivo, o status de aprovação, a etapa responsável
pela decisão, a categoria identificada e os motivos encontrados.

### `GET /api/saude`

Verifica:

- se o Ollama está respondendo;
- se o modelo de visão está disponível para uso.

### `POST /api/uploadHandwriting`

Recebe uma imagem e solicita a extração do texto ao modelo configurado para
OCR. O retorno contém o nome do arquivo e o texto extraído.

## Tecnologias utilizadas

- **Frontend:** React, TypeScript, Vite e React Router.
- **Backend:** Python, FastAPI, Pydantic e OpenCV.
- **IA:** Ollama com modelo de visão compatível, como `llava`.
- **Proxy reverso:** Nginx.
- **Execução:** Docker e Docker Compose.

## Como executar

### Pré-requisitos

- Docker Desktop ou Docker Engine com Docker Compose;
- aproximadamente o espaço em disco necessário para as imagens Docker e o
  modelo de IA;
- opcionalmente, GPU NVIDIA configurada para acelerar o Ollama.

### Subir a aplicação

Na raiz do projeto, execute:

```bash
docker compose up -d
```

Para acompanhar os logs em primeiro plano:

```bash
docker compose up
```

O serviço de inicialização do Ollama baixa o modelo configurado antes de o
backend realizar as análises. Para acompanhar esse processo:

```bash
docker compose logs -f ollama-init
```

Depois, acesse:

```text
http://localhost/
```

O backend também é exposto diretamente em:

```text
http://localhost:3000
```

### Encerrar a aplicação

```bash
docker compose down
```

Para remover também os volumes locais associados aos serviços:

```bash
docker compose down -v
```

> A remoção dos volumes pode apagar o modelo baixado do Ollama e exigir um novo
> download na próxima inicialização.

## Estrutura do projeto

```text
.
├── Back-end/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── config.py       # Configurações da aplicação e dos critérios
│   │   ├── main.py         # Criação da aplicação FastAPI
│   │   └── schemas.py      # Contratos das requisições e respostas
│   ├── routes/
│   │   └── images.py       # Endpoints de upload, análise e saúde
│   └── services/
│       ├── technician.py   # Validações técnicas com OpenCV
│       ├── vision.py       # Integração com o Ollama
│       └── outpainting.py   # Serviço de expansão de imagem
├── Front-end/
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   └── app/
│       └── src/
│           ├── App.tsx
│           └── components/
│               ├── FileLoader.tsx
│               └── LanguageSelector.tsx
├── docker-compose.yaml
└── nginx.conf
```

## Desenvolvimento

O Compose observa alterações no código durante o desenvolvimento:

- alterações em `Back-end/app` são sincronizadas no container do backend;
- alterações em `Front-end/app` são sincronizadas no container do frontend;
- mudanças nos arquivos de dependências provocam a reconstrução do serviço
  correspondente.

Para executar os comandos do frontend localmente:

```bash
cd Front-end/app
npm install
npm run dev
```

Comandos disponíveis:

```bash
npm run build
npm run lint
npm run preview
```

## Observações

- O primeiro uso pode demorar enquanto o Ollama baixa o modelo.
- Uma falha na etapa técnica não chama o modelo de IA, reduzindo tempo e
  consumo de recursos.
- O nome e a URL do modelo são tratados pela configuração do backend e pelas
  variáveis do serviço no Compose.
- O diretório usado para os modelos do Ollama é persistido em volume para evitar
  downloads repetidos.
