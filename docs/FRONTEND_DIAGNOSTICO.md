# Diagnóstico do frontend da POC

## Problemas encontrados no frontend recebido

- Telas mantinham arrays independentes e ações sem persistência compartilhada.
- Projetos, artes e aprovações não possuíam relacionamentos consistentes.
- Botões confirmavam sucesso sem aguardar qualquer operação.
- Login, dados de campanha e resultados simulados estavam misturados no mesmo estado local.
- Recarregar uma rota interna redirecionava antes do carregamento dos dados.
- Havia mensagens que sugeriam análise/correção mesmo sem resultado processado.

## Estado atual

- Apenas a sessão de login demonstrativo permanece no `localStorage`.
- Projetos, briefings, artes, versões, análises e decisões vêm da API `/api/v1`.
- Trocar Criador/Revisor muda a persona demo enviada no header e recarrega os mesmos dados persistidos.
- Ações aguardam a resposta HTTP e apresentam erros reais.
- Rotas internas mostram carregamento durante a hidratação.
- Uploads exibem somente resultados produzidos pelo OCR e pelas regras locais.
- Briefings PDF/DOCX/TXT são extraídos, mas todo campo continua editável para confirmação humana.
- Templates estruturados oferecem geração multicanal, prévia e nova versão reais.
- PNG/JPG arbitrário não recebe uma falsa correção visual.

## Limites

- O login não autentica uma pessoa real.
- Não há publicação em canais externos.
- Processamento em segundo plano usa a infraestrutura simples da POC.
- Aprovação é uma decisão humana de demonstração, não uma garantia regulatória.
