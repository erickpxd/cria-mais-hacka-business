# POC Cria Mais — diagnóstico e implementação

## Problemas encontrados

- O frontend mantinha dados e ações em mocks/localStorage, enquanto o backend possuía outra fonte de dados.
- As rotas não tinham versão, a identidade demo assumia Ana silenciosamente e imagens dependiam de autenticação incompatível com `<img>`.
- Os estados usavam nomes divergentes (`precisa_ajustes` e `precisa_de_ajustes`) e não havia uma máquina de transições central.
- Upload, projeto, arte, análise e decisão existiam, mas não formavam um fluxo único consumido pela interface.
- Correção de bitmap e adaptação aparentavam ser confiáveis apesar de não preservarem camadas editáveis.
- O banco era criado implicitamente, sem migração reproduzível, e não havia suíte de testes.
- O OCR estava configurado com idioma inexistente (`latin`) e depois apresentou incompatibilidade oneDNN em CPU.
- A interface confirmava submissões antes da resposta HTTP e redirecionava rotas internas durante o carregamento.
- Após uma devolução, a interface não oferecia upload de uma nova versão vinculada à mesma arte.

## O que a POC executa de verdade

- Login mockado exclusivamente no frontend e alternância entre Ana (Criador) e Rafael (Revisor). Ele apenas escolhe a persona enviada à API.
- SQLite persistente, migração Alembic e armazenamento local de originais/versões.
- Criação e consulta de projetos com briefing manual e canais.
- Upload validado de PNG/JPG, incluindo MIME, conteúdo, tamanho e limite de pixels.
- OCR local experimental com PaddleOCR e verificações determinísticas; falhas ficam registradas como `erro` e não bloqueiam o fluxo humano.
- Processamento rastreável com estados `queued`, `processing`, `completed` e `failed`, consultados automaticamente pelo frontend.
- Extração determinística de PDF/DOCX/TXT, mantendo campos ausentes e preços conflitantes explícitos para confirmação humana.
- OCR de fallback para páginas PDF escaneadas, limite de páginas e leitura de tabelas DOCX.
- Geração multicanal real por template estruturado, com dimensões específicas por canal.
- Prévia lado a lado de alterações do template e persistência em nova versão, mantendo a anterior imutável.
- Estados centralizados: análise, produção, ajustes, espera de aprovação e aprovação.
- Submissão, fila do revisor, devolução com comentário obrigatório, aprovação humana e exportação da versão aprovada.
- Nova versão vinculada à arte devolvida, sem sobrescrever a original.
- Frontend abastecido pela API `/api/v1`; localStorage guarda apenas a sessão demo.
- Health checks básico e de dependências.

## Limites declarados

- `X-Demo-User` é seleção de persona, não autenticação nem autorização de produção.
- Correção automática de PNG/JPG e adaptação multicanal retornam HTTP 501. Elas exigem um template editável para serem confiáveis.
- O parser de documentos associa/extrai dados, mas o formulário atual mantém confirmação manual como fonte segura.
- `BackgroundTasks` é adequado somente à demonstração; produção precisa de fila durável.
- Não há publicação em canais, IA generativa, garantia jurídica/regulatória ou integração corporativa.
- SQLite e storage local devem ser substituídos por banco e armazenamento apropriados antes de exposição pública.

## Evidências de validação

- Testes automatizados de domínio, análise de preço, PDF escaneado e integração HTTP: `11 passed`.
- Lint Python com Ruff: aprovado.
- Frontend: ESLint e build Vite concluídos sem erro.
- E2E Playwright/Chrome: login demo → projeto → template → prévia → nova versão → submissão → troca para Revisor → aprovação → retorno ao Criador.
- Dependências completas do frontend: `npm audit` sem vulnerabilidades conhecidas.
- Imagem Python: `pip-audit` sem vulnerabilidades conhecidas.
- PostgreSQL 17: migrations até o `head` e criação/leitura de projeto validadas em container; SQLite permanece o padrão local.
- Backend: compilação Python, configuração do Compose, build da imagem e migração Alembic concluídos.
- Smoke/E2E HTTP executado: ausência de identidade (401), criação/listagem, upload, OCR concluído, submissão, bloqueio de aprovação pelo criador (403), fila do revisor, aprovação e upload de nova versão.

