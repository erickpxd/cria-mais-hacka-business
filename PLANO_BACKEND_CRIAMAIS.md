Cria Mais — Plano de backend para a POC
Versão: 1.0 — 25/10/2026
Propósito: transformar o frontend demonstrativo em um fluxo real, barato, rastreável e coerente.
Prazo do desafio: 26/10/2026. O corte P0 abaixo é a única meta para a apresentação; P1/P2 são incrementos, não promessas de entrega.
Documento de planejamento, não evidência de que o backend já esteja implementado. Conferir a estrutura real do repositório e os contratos atuais do frontend antes de executar.

1. Visão do produto
O Cria Mais organiza projetos por briefing, recebe artes, verifica inconsistências, propõe correções, permite ao criador aceitar/rejeitar um diff real, e envia a versão resultante a uma aprovação humana.

Dois atores humanos: Criador (envia, corrige, adapta, submete) e Revisor (aprova ou devolve com comentário). O sistema executa a pré-revisão, não substitui o parecer humano. A troca de perfis no login demonstrativo não é autenticação de produção.

Regras inegociáveis:
- Usar somente dados sintéticos ou material público permitido. Nunca assumir acesso a dados internos da empresa.
- Nunca inventar dados do briefing. Campo ausente = not_found; ambiguidade = needs_confirmation; conflito = conflict. Extratos e referências ao documento acompanham os valores propostos.
- Nunca chamar resultado mockado de análise real. Se o pipeline não processou o arquivo, retornar indisponibilidade ou estado pendente.
- O PNG/JPG original é imutável. Identificar texto num bitmap não significa conseguir editá-lo fielmente. A correção automática visual só é oferecida para template SVG/HTML editável controlado ou para reconstrução explicitamente aprovada.
- Toda correção deve ter evidência, proposta concreta, arte/versão vinculadas, estado de decisão, e efeito verificável na renderização final.
- Nenhuma peça é aprovada/publicada automaticamente. Avisos regulatórios exigem revisão especializada, não alegações de compliance legal completo.
- Minimizar APIs pagas: regras, parsing, OCR local e templates antes de modelos generativos. ML tradicional só quando existir histórico rotulado suficiente e avaliação adequada.
2. Arquitetura recomendada
Monólito modular em Python / FastAPI. É a menor solução plausível para a POC, separando domínio e integrações para crescer depois.
React + TypeScript (frontend atual)
             |
             | HTTP /api/v1 + upload multipart
             v
      FastAPI (API REST)
      |  projetos / briefings / artes / análises / versões / aprovações
      |  schemas Pydantic, validação, serviços de domínio
      |
      +--> Banco relacional: SQLite na demo local;
      |                      PostgreSQL na implantação/equipe, via SQLAlchemy + Alembic
      |
      +--> Storage local privado /storage (POC)
      |        original.pdf, original.png, versions/*.svg, previews/*.png
      |
      +--> Processadores locais
      |      - briefing: PDF/DOCX/TXT -> texto com proveniência
      |      - arte: OCR -> caixas + confiança
      |      - regras: texto, preço, canal, dimensão, campos obrigatórios
      |      - correção: SVG/HTML-template -> versão + diff
      |      - adaptação: SVG/HTML-template -> PNG em outro formato
      |
      +--> Registro de eventos / auditoria e medições
Fila de processamento: não começar com microsserviços, Kafka, Redis ou GPU. Para documentos pequenos, uma tarefa controlada no processo ou BackgroundTasks com estado queued/processing/completed/failed é aceitável apenas na POC, com limite e timeouts. Há risco de perda de jobs em reinício. Para execução persistente ou OCR pesado em produção, migrar para worker externo + fila durável (por exemplo Redis/RQ), sem mudar as rotas nem o contrato.

Stack sugerida: FastAPI, Pydantic, SQLAlchemy, Alembic, SQLite inicialmente, python-docx, pdfplumber ou pypdf, Pillow, pytesseract + tesseract-ocr-por, pytest, httpx. OpenCV só para verificações de layout que realmente forem implementadas. PaddleOCR é alternativa futura se os testes locais mostrarem ganho significativo frente ao Tesseract. Confirmar licenças das dependências e dos modelos antes da adoção empresarial.
3. Modelo mínimo de dados
Entidade	Campos indispensáveis	Observações
Project	id, name, status, created_at, updated_at	Um projeto é uma campanha
BriefingVersion	id, project_id, version, source_type, original_file_id?, confirmed_at?, created_at	Nunca alterar uma versão confirmada em silêncio
BriefingField	id, briefing_version_id, key, value?, state, source_page?, source_excerpt?, source_block?, confirmed	Rastreabilidade e ausência explícita
Deliverable	id, project_id, channel, format_key, required, width?, height?	Formatos exigidos por briefing
FileAsset	id, owner_type, owner_id, content_type, size, sha256, storage_key, created_at	Binários fora do banco; chave interna opaca
Artwork	id, project_id, deliverable_id?, title, status, current_version_id?	Nunca perder o vínculo de projeto
ArtworkVersion	id, artwork_id, number, source_asset_id, preview_asset_id?, editable_asset_id?, briefing_version_id, created_at	Original preservado; versões imutáveis
AnalysisRun	id, artwork_version_id, briefing_version_id, status, engine_version, started_at?, finished_at?, error_code?	Resultado reproduzível e diagnóstico
Finding	id, analysis_run_id, type, severity, status, evidence, bbox?, expected?, observed?, confidence?	Não afirmar erro sem evidência
Correction	id, finding_id, operation, target_element_id?, before, after, decision, output_version_id?	accept/reject separado de aplicar/gerar
Review	id, artwork_version_id, status, submitted_at, decided_at?, reviewer_demo_id?	Aprovação de versão específica
ReviewComment	id, review_id, text, x?, y?, created_at	Comentário com coordenadas normalizadas opcionais
AuditEvent	id, project_id, entity_type, entity_id, action, actor, timestamp, details	Aceitação, rejeição, devolução e aprovação


Não é necessário criar tudo de uma só vez. Project, BriefingVersion, Artwork, ArtworkVersion e Review + seus serviços são a espinha dorsal P0. AnalysisRun/Finding/Correction entram quando o processamento real estiver conectado.
Estados
Artwork: em_producao -> precisa_de_ajustes -> aguardando_aprovacao -> aprovada. Pode ir direto de em_producao a aguardando_aprovacao quando permitido. Devolução exige comentário; nova submissão cria nova revisão e, após editar, nova versão.

AnalysisRun: queued, processing, completed, failed, unsupported. Este estado não é o status da arte.

Finding: confirmed, uncertain, not_applicable — não misturar com Correction.decision: pending, accepted, rejected.

Regra de consistência: não aprovar versão X e depois alterar o arquivo por trás de X; versões são imutáveis. Mudança de briefing cria nova versão e pode invalidar análises anteriores.
4. Entrega P0 — vertical real de ponta a ponta
P0-A — Persistência e ciclo de revisão (obrigatório)
1. Ler o frontend atual (App.tsx, rotas, serviços, mocks, tipos) e registrar o contrato real. NÃO supor que endpoints inexistentes já estão implementados.
2. Criar FastAPI, banco SQLite, migrations e armazenamento local privado.
3. Criar/consultar projetos; salvar briefing manual confirmado; cadastrar canais exigidos.
4. Fazer upload real de PNG/JPG com limites e prévia servida por endpoint de arquivo.
5. Listar artes do projeto e gerenciar estados reais com IDs coerentes.
6. Criar submissão para revisão, devolver com comentário obrigatório ou aprovar versão específica.
7. Fazer o frontend consumir essas rotas; desativar apenas os mocks substituídos e preservar o modo demo com aviso.
8. Demonstrar reload de página sem perder campanha, arte ou status.
Critério P0-A: criar projeto → adicionar arte → enviar à aprovação → alternar papel demo → comentar/devolver ou aprovar → resultado refletido na tela do criador, sem mocks desconectados.
P0-B — Primeira análise REAL de baixo custo (prioridade máxima após P0-A)
Usar um briefing sintético controlado como fonte confirmada, por exemplo: produto Shampoo 400 ml, preço R$ 17,90, canais feed e stories. Enviar PNG/JPG contendo claramente R$ 19,90.
1. Extrair texto e caixas da arte com OCR local (tesseract + pacote por, orientação/testes).
2. Normalizar moeda BRL com Decimal (não float).
3. Comparar valores apenas com produtos e preços efetivamente confirmados no briefing; se múltiplos produtos tornarem a associação ambígua, marcar uncertain.
4. Retornar Finding contendo valor observado, valor esperado, evidência do briefing, caixa normalizada da arte e nível de confiança do OCR.
5. Identificar o formato exigido que não recebeu arte.
6. Mostrar resultados verdadeiros na tela existente de análise; se OCR falhar, devolver failed/uncertain, não inventar correção.
Critério P0-B: mudar os dados na imagem de teste altera o resultado detectado; upload de imagem diferente não retorna um resultado fixo. Um briefing com preço igual não recebe falsa divergência de preço.
P0-C — Primeira correção e adaptação REAIS (meta essencial para atender geração multicanal do desafio; escopo mínimo)
Fluxo confiável: oferecer um template editável SVG/HTML com campos product_name, price, disclaimer, logo_placeholder, image_asset. O template pode ser renderizado como PNG. No diff, trocar price e/ou texto atualiza uma nova renderização; aceitar/rejeitar gera saída diferente, sem modificar o original.
- A partir de um briefing confirmado, gerar um criativo de template por canal (ex.: quadrado 1080×1080 e vertical 1080×1920).
- Calcular zonas seguras, caixa de texto e tamanho de fonte; não esticar o bitmap original.
- Comparar prévias original/corrigida lado a lado e destacar elemento alterado com coordenadas reais.
- Persistir ArtworkVersion criada pela alteração aceita e permitir exportar PNG.
- Corrigir ou adaptar PNG/JPG arbitrário é explicitamente unsupported quando não há informação de camadas. Oferecer reconstrução pelo template, com confirmação do criador e indicação de que a composição poderá mudar.
Critério P0-C: selecionar/rejeitar correções modifica de fato o conteúdo renderizado e a versão exportada. Alterar canal muda a composição, não apenas o CSS de exibição.
P0-D — Evidência de ganho (se houver tempo)
Armazenar timestamps: upload, análise iniciada/concluída, correção confirmada, envio ao revisor, aprovação/devolução. Exibir no pitch comparação mensurável entre execução manual da tarefa e assistida. Não alegar economia real sem medir amostras e não confundir tempo de CPU com tempo humano.
5. P1/P2 — posterior, fora da promessa da apresentação
P1: parser robusto de PDFs/DOCX com tabelas e origem por página, OCR em PDFs escaneados, mais tipos de regra visual, extração de datas/validades, atualização de briefing invalidando análises, fila externa, melhorias de contraste e legibilidade.

P2: ML tradicional para ranking de risco de retrabalho e sugestões de template a partir de correções rotuladas; métricas comerciais apenas com dados de campanhas disponíveis e autorizados; integrações com ferramentas da empresa; autenticação real, RBAC, observabilidade, auditoria operacional completa; geração paga apenas sob demanda e com orçamento definido.

Não treinar um classificador em dezenas de artes sintéticas e anunciar precisão empresarial. Datasets externos são base para experimentos, não substituem validação no domínio.
6. Estratégia de leitura de briefing — sem alucinação
- DOCX: python-docx lendo parágrafos e tabelas; guardar índice/trecho e nome da tabela quando aplicável.
- PDF digital: pdfplumber/pypdf, preservando número de página e trecho. PDF não garante ordem de leitura correta.
- TXT: texto por linhas, com offsets.
- PDF escaneado: OCR local apenas como fallback, rotulando origem ocr e confiança/inconsistências.
- Extração estruturada: mapeamento determinístico de padrões explícitos como Produto:, Preço:, Canais:. Não inferir valor que não aparece. Exibir not_found, needs_confirmation e conflict.
- Confirmação humana: após análise, mostrar cada campo, origem e dados ausentes. Só a versão confirmada vira fonte de verdade para checagem de arte.
- Múltiplos preços/produtos: não associar com suposição. Solicitar que usuário vincule produto/preço ou marcar pendência.
Resposta ilustrativa (contrato sugerido, revisar com frontend):
{
  "briefingId": "uuid",
  "version": 1,
  "status": "needs_confirmation",
  "fields": [
    {
      "key": "product_name",
      "value": "Shampoo 400 ml",
      "state": "found",
      "source": {"page": 1, "excerpt": "Produto: Shampoo 400 ml", "method": "digital_text"}
    },
    {"key": "end_date", "value": null, "state": "not_found", "source": null}
  ]
}
7. API HTTP sugerida — /api/v1
Método	Caminho	Responsabilidade
GET	/health	saúde básica e dependências essenciais
GET/POST	/projects	listar/criar projetos
GET	/projects/{project_id}	detalhes e referência do briefing atual
POST	/projects/{project_id}/briefings/upload	receber PDF/DOCX/TXT e iniciar extração
POST	/projects/{project_id}/briefings/manual	criar briefing manual
GET	/projects/{project_id}/briefings/{briefing_id}	resumo, estado e origem dos campos
POST	/projects/{project_id}/briefings/{briefing_id}/confirm	validar e confirmar fonte da verdade
GET/POST	/projects/{project_id}/artworks	listar e criar via multipart
GET	/artworks/{artwork_id}	detalhe, versões e status
POST	/artworks/{artwork_id}/analyses	disparar análise da versão selecionada
GET	/analyses/{analysis_id}	polling do estado, findings e evidências
POST	/artworks/{artwork_id}/corrections/preview	renderizar seleção de alterações reais
POST	/artworks/{artwork_id}/corrections/commit	persistir nova versão editável
POST	/artworks/{artwork_id}/adaptations	gerar nova versão de template para um canal
POST	/artworks/{artwork_id}/submit	submeter versão específica para revisão
GET	/approvals	listar só versões submetidas
POST	/reviews/{review_id}/comments	inserir comentário
POST	/reviews/{review_id}/approve	aprovar versão submetida
POST	/reviews/{review_id}/request-changes	devolver com comentário obrigatório
GET	/assets/{asset_id}	acesso controlado aos binários


Contratos relevantes:
- POST /artworks/{id}/analyses recebe artworkVersionId e briefingVersionId. Retorna 202 Accepted e analysisId para processamento assíncrono; se optar por execução síncrona na demo, documentar isso claramente.
- Resultados têm schemaVersion, engineVersion, IDs e status explícitos, sem textos aleatórios.
- Cada finding inclui { id, type, severity, status, observed, expected, evidence, bbox, confidence, correctionSupported }. bbox normalizada em [0,1] e vinculada à largura/altura da imagem.
- POST /corrections/preview recebe { baseVersionId, acceptedCorrectionIds: [] }; rejeitadas não alteram a saída.
- Aprovação aceita reviewId + versão submetida e rejeita versão incorreta, duplicação e estados inválidos com 409 Conflict.
- Respostas de erros: HTTP 400/404/409/413/415/422/500 conforme semântica, com { code, message, details? } e mensagens que permitam ao frontend ajudar o usuário.
- Endpoints listados são proposta; consolidar nomes com as funções/rotas reais do frontend antes de implementá-los.
8. Estrutura sugerida de projeto
backend/
  pyproject.toml
  .env.example
  alembic.ini
  app/
    main.py
    core/config.py
    core/errors.py
    api/v1/{projects,briefings,artworks,analyses,corrections,approvals,assets}.py
    domain/{models,schemas,enums}.py
    db/{base,session,migrations}/
    repositories/
    services/{project_service,briefing_service,artwork_service,review_service}.py
    processing/{document_reader,ocr_engine,rule_engine,template_renderer}.py
    storage/local.py
  tests/{unit,integration,fixtures}/
  storage/                 # gitignored
Evitar criar diretórios vazios e abstrações artificiais. É recomendação, não ordem para reescrever arquitetura já estabelecida.
9. Segurança e conformidade mínima
- Demo com perfil fictício não constitui autorização real; limitar uso a ambiente controlado. Não expor o backend publicamente sem autenticação e autorização.
- Upload: extensões permitidas, bytes/assinatura validados, limite de 20 MB coerente com frontend, limite de páginas/dimensões, filenames randomizados, storage privado, tipos não executáveis; sanitizar SVG caso seja recebido (preferível gerar SVG editável no servidor a partir de templates próprios).
- Limitar processamento por arquivo e recursos; proteger contra imagens maliciosas e arquivos compactados, quando aplicável.
- CORS restrito às origens do frontend; secrets em variáveis de ambiente; nunca salvar credenciais de produção no Git.
- Em produção: isolamento do processador, malware scanning e políticas de retenção/acesso aos uploads.
- Manter originais, versões e evidência; registrar quem aprovou. Não publicar nem gerar alegação de conformidade farmacêutica automática.
- Licenças: verificar PyMuPDF caso seja considerado (AGPL/comercial) e preferir bibliotecas adequadas ao uso; manter inventário de licenças de modelos e fontes.
10. Testes de aceitação indispensáveis
1. Briefing sem data retorna not_found, nunca data inventada.
2. PDF com dois preços divergentes marca conflito/ambiguidade, não escolhe valor arbitrário.
3. Imagem com preço diferente do briefing confirmado gera finding com evidência; imagem correta não gera esse finding.
4. OCR incerto não emite confirmed sem evidência confiável.
5. Arquivo inválido/maior que 20 MB é rejeitado consistentemente com o frontend.
6. Projeto A nunca mostra arte/briefing/análise do projeto B.
7. Aceitar e rejeitar uma correção mudam de verdade a renderização do template; original inalterado.
8. Adaptação horizontal/vertical realmente recompõe conteúdo, não estica PNG.
9. Aprovação de versão errada ou de arte não submetida retorna 409.
10. Devolução sem comentário é rejeitada; com comentário retorna ao criador e mantém histórico.
11. Reiniciar aplicação não perde metadados e arquivos salvos (em deployment com volume persistente).
12. Rodar pytest, lint do backend e teste E2E do frontend, registrando evidências, não apenas declarando sucesso.
11. Ordem de trabalho e definição de pronto
Ordem: (1) inspeção do frontend e contratos; (2) banco + CRUD e uploads; (3) revisão/aprovação real; (4) parser de briefing; (5) OCR + regra de preço; (6) diff/template + multiformato se houver margem; (7) testes, documentação e pitch.

Corte de escopo: o enunciado exige uma demonstração funcional de criação/variação e adaptação multicanal. Por isso, priorize um único template real que gere pelo menos Feed e Stories a partir do briefing, mesmo que a análise visual mais sofisticada fique fora. Se nem isso for viável até o prazo, mostre apenas o que foi implementado e declare a lacuna, sem maquiar o resultado. Em qualquer cenário, o diff de PNG arbitrário deve ser sinalizado como não suportado quando não houver camadas editáveis.

Pronto significa: servidor executável, API documentada em /docs, env.example, persistência, upload validado, dados sintéticos, scripts de inicialização, testes automatizados da regra de preço e do fluxo de aprovação, integração real com rotas existentes e uma demo de ponta a ponta reproduzível.
12. Referências técnicas consultadas
- FastAPI — upload de arquivos: https://fastapi.tiangolo.com/tutorial/request-files/
- FastAPI — tarefas em segundo plano e limitações: https://fastapi.tiangolo.com/tutorial/background-tasks/
- Tesseract — instalação e idiomas: https://tesseract-ocr.github.io/tessdoc/Installation.html
- pdfplumber — texto e posições: https://github.com/jsvine/pdfplumber
- pypdf — extração de texto: https://github.com/py-pdf/pypdf
- OWASP — segurança de uploads: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html