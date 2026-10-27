Tarefa para o Codex — Recuperar e organizar o frontend do Cria Mais
Atue como engenheiro de software sênior e responsável técnico pelo produto, não como um gerador automático de telas. O frontend foi produzido rapidamente a partir do Figma e possui fluxos quebrados, mocks inconsistentes e interações sem sentido. Sua missão é entender o que existe e transformá-lo numa POC coerente, simples e demonstrável, sem reescrever desnecessariamente o projeto.
Leia primeiro
1. AGENTS.md na raiz do repositório: é a referência permanente de produto, UX, regras de negócio e escopo.
2. Código existente (comece por package.json, src/App.tsx, src/App.css, rotas, componentes e estado).
3. Figma pelo MCP já conectado: https://www.figma.com/design/dChv0jhQZXykOgSYfHwmA0/Sem-t%C3%ADtulo?node-id=0-1
Não assuma que tudo no frontend atual funciona só porque lint e build passaram. Primeiro traceie os fluxos reais pelo código e veja como cada tela chega à seguinte.
Etapa A — Diagnóstico e engenharia
- Descubra a arquitetura atual, dependências, lógica de navegação, estado e persistência.
- Liste os mocks, botões sem efeito, rotas inválidas, páginas sem dados coerentes e estados desconectados.
- Verifique se há tudo concentrado em App.tsx e quais responsabilidades precisam ser extraídas.
- Identifique componentes e assets que já correspondem ao Figma.
- Crie/atualize docs/FRONTEND_DIAGNOSTICO.md com: problemas observados, causa, prioridade, correção proposta e decisões tomadas.
- Não permaneça apenas no diagnóstico: use-o para guiar a implementação na mesma execução.
Etapa B — Login para POC (prioridade alta)
Implementar /login com a aparência do Cria Mais. Como é uma POC, não implementar autenticação de produção.
- Um botão principal: "Entrar na demonstração".
- Ao clicar, preencher automaticamente a identidade fictícia (se existirem inputs), registrar uma sessão local de demonstração e encaminhar ao dashboard / sem exigir digitação.
- Usar usuário fictício padrão com papel Criador.
- Permitir trocar para Revisor pelo menu do perfil, para demonstrar a segunda jornada, e voltar para Criador.
- Adicionar opção Sair.
- Rotas protegidas apenas pela presença da sessão local de demonstração; sem sessão, encaminhar ao login.
- Exibir "Ambiente demonstrativo — sem autenticação real" de modo discreto.
- Não salvar credenciais de verdade, não usar tokens fictícios apresentados como seguros.
Experiência desejada: abrir o sistema → clicar uma vez em "Entrar na demonstração" → acessar projetos. Ao trocar de perfil, enxergar aprovações pendentes daquele mesmo conjunto de artes.
Etapa C — Dar significado aos dados e corrigir os fluxos
Trocar conjuntos dispersos de mocks por um único estado de POC consistente. Pode usar armazenamento local, sem backend, mas as ações precisam provocar mudanças reais e coerentes.

Implementar ou corrigir:
1. Projetos: criar projeto manualmente, listar, abrir por ID, preservar dados; estados vazios e projetos sintéticos separados.
2. Briefing: o formulário manual cria dados de verdade no estado local. Para PDF/DOCX sem parser/backend, mostrar que a extração automática ainda não está conectada; permitir transcrição/conferência manual, sem inventar dados extraídos.
3. Artes: associar upload ao projeto correto; preview real do arquivo recebido; metadados de canal e formato; validações de arquivo e mensagens claras.
4. Análise: só exibir resultado "analisado" se houver dados de análise de fato, mesmo que de um cenário demonstrativo explicitamente escolhido. Não associar sempre os mesmos erros ao arquivo enviado. Caso contrário, informar recurso ainda não conectado e permitir seguir por fluxo manual de aprovação.
5. Diff: um conjunto de correções está ligado a uma arte/versão. Aceitar/rejeitar precisa atualizar a proposta visível, sem alterar original. Se ainda não for possível corrigir arquivos PNG/JPG arbitrários, limitar a experiência funcional a templates/elementos editáveis e comunicar a limitação.
6. Aprovações: ao enviar uma arte, ela deve surgir na fila do revisor; aprovar ou devolver muda os dados exibidos para ambos. Devolver requer comentário. Evitar filas mockadas desconectadas.
7. Adaptação: se houver adaptação determinística real por templates, use-a; caso contrário, não afirmar que houve adaptação inteligente. A UI não deve apresentar um simples resize como geração válida.
8. Histórico: armazenar pelo menos data, ação, papel e comentário; ao criar nova versão, preservar a original.
Prefira menos funcionalidades realmente coerentes a várias telas que fingem funcionar.
Etapa D — Refatoração proporcional
- Quebre componentes monolíticos quando a complexidade justificar, com organização por funcionalidades.
- Centralize tipos do domínio, regras de transição de status, rotas e dados de demonstração.
- Separe componentes de apresentação de hooks/serviços de estado.
- Crie uma interface de repositório/serviço que possa receber backend no futuro sem alterar toda a UI.
- Remova código morto, duplicações e handlers decorativos.
- Preserve estilos/tokens/assets do Figma; não redesenhe a plataforma.
- Evite dependências novas e abstrações excessivas: isso ainda é uma POC.
Etapa E — Verificar a jornada no navegador
Validar as seguintes histórias, em ordem:

História 1: usuário abre /login, clica em "Entrar na demonstração", vê o dashboard e consegue sair.

História 2: criador cria projeto manualmente; abre o projeto e encontra o briefing que acabou de cadastrar, não um briefing genérico de outro projeto.

História 3: criador envia arte PNG/JPG; a miniatura aparece somente naquele projeto. Ao recarregar, a interface não deve exibir um blob: quebrado; persistir o arquivo de modo apropriado ou informar que a prévia é temporária.

História 4: criador envia arte à aprovação; troca para Revisor; vê a arte; devolve com comentário; troca para Criador e encontra essa pendência.

História 5: criador reenvia a arte; revisor aprova; o status passa a "Aprovada" em todas as áreas.

História 6: a tela de diff, quando houver uma proposta editável real, aplica aceitação/rejeição independentemente e preserva original; quando não houver, comunica honestamente a indisponibilidade.

História 7: links, breadcrumbs, filtros, navegação, campos, estados vazios e botões têm comportamento coerente e feedback ao usuário.

Execute os scripts existentes de lint, build e testes. Se puder abrir a aplicação em navegador/testes E2E, valide o fluxo também visualmente e compare o resultado com o Figma. Não declare fluxos aprovados se não foram testados.
Priorização e entrega
P0: login demo em um clique; navegação coerente; estado único; projetos/briefings; upload; fila de aprovação real; ações de aprovar/devolver; saída/troca de perfil.

P1: diff funcional para casos editáveis; tratamento correto de formatos; persistência de arquivos; melhorias de UX e acessibilidade.

P2: infraestrutura para OCR, extração, IA/ML e integrações futuras, apenas contratos e pontos de extensão — sem serviços pagos nem backend fictício.

Ao concluir, entregue um resumo objetivo:
- Causas dos principais bugs e como foram corrigidos.
- Arquivos e módulos alterados.
- Fluxos que funcionam localmente, de ponta a ponta.
- Recursos apenas demonstrativos ou pendentes de backend.
- Resultado real de npm run lint, npm run build e testes executados.
- Comandos para executar a aplicação.
- Riscos conhecidos e próximo passo técnico mais importante.
Não pare depois de produzir um plano. Faça a refatoração e a correção dos fluxos em código, de forma incremental, preservando o que já funciona.