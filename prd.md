# PRD — Agente Smith: Sistema Multi-Agente de Profissionalização da Gestão iDVL

## 1. Resumo Executivo

O Agente Smith é um sistema multi-agente autônomo construído no n8n que conduz o
projeto de profissionalização da gestão da iDVL Tecnologia Contábil. Inspirado nos
princípios de Adam Smith — divisão do trabalho, especialização, acumulação de capital
organizacional — o próprio sistema é arquitetado com divisão de trabalho entre agentes:
cada sub-agente tem função única e bem definida, e um orquestrador coordena o fluxo.

O sistema interage com o CEO via WhatsApp, entrevista a equipe, mapeia processos,
escreve SOPs, produz diagnósticos econômicos e acompanha o progresso do projeto de
forma autônoma, solicitando aprovação humana apenas nas decisões críticas.

---

## 2. Problema / Oportunidade

A iDVL opera com processos não documentados, dependência de pessoas-chave e o sócio
fundador alocado em execução operacional em vez de estratégia. A profissionalização da
gestão exige um projeto estruturado em 5 fases que, se conduzido manualmente, consumiria
meses de energia do CEO. O Agente Smith automatiza a condução deste projeto, liberando
o CEO para aprovar e decidir — não para executar.

---

## 3. Requisitos Funcionais

### RF01 — Onboarding com CEO via WhatsApp
- O sistema envia mensagens ao CEO via WhatsApp ao ser ativado pela primeira vez
- Conduz roteiro de 9 perguntas em blocos (contexto, pessoas, expectativas)
- Uma pergunta por mensagem, aguarda resposta antes de prosseguir
- Salva todas as respostas em `contexto.json` no Google Drive
- Ao finalizar, envia resumo e inicia Fase 1 automaticamente

### RF02 — Entrevistas com equipe
- Com base nos nomes fornecidos pelo CEO, o sistema agenda entrevistas assíncronas via WhatsApp
- Cada entrevistado recebe roteiro padronizado: o que faz, tempo estimado por tarefa, o que trava, quem depende dele
- Respostas salvas individualmente em `/entrevistas/{nome}-{data}.json`
- Ao concluir todas as entrevistas de uma fase, notifica o orquestrador

### RF03 — Mapeamento de processos
- Com base nas entrevistas, o sub-agente Mapeador gera documento estruturado
- Formato: processo, responsável atual, etapas, tempo estimado, gargalo, dependência de pessoa
- Produz arquivo `fase-1-mapa-processos.md` no Google Drive
- Identifica e sinaliza: trabalho produtivo x improdutivo, pontos de falha únicos

### RF04 — Redação de SOPs
- O sub-agente Redator recebe mapas de processo como insumo
- Gera SOP para cada processo crítico usando template padronizado
- Aplica autorreflexão: revisa o próprio SOP antes de salvar
- Salva em `/sops/{nome-processo}-v{n}.md`
- Notifica CEO para revisão e aprovação

### RF05 — Diagnóstico econômico por fase
- O sub-agente Analista aplica os princípios de Smith a cada fase concluída
- Identifica: capital fixo mal alocado, incentivos desalinhados, trabalho improdutivo
- Produz relatório de diagnóstico por fase em `/relatorios/diagnostico-fase-{n}.md`
- Inclui: achado, princípio smith aplicável, recomendação, trade-offs

### RF06 — Follow-up semanal automático
- Toda sexta-feira às 8h, o sistema envia resumo ao CEO via WhatsApp
- Formato: concluído / pendente / precisa de decisão
- Se uma tarefa atrasar mais de 48h, envia alerta imediato
- Registra todas as decisões do CEO em `log-decisoes.md`

### RF07 — Fluxo de aprovação
- Antes de avançar entre fases, o sistema solicita aprovação do CEO via WhatsApp
- Formato: "Antes de avançar: [descrição]. Responda OK ou Ajusta"
- Se CEO responder "Ajusta", o sistema pergunta o que deve mudar e reprocessa
- Aprovações ficam registradas no log com timestamp

### RF08 — Memória persistente
- Todo o estado do projeto é armazenado no Google Drive
- Estrutura de pastas padrão criada automaticamente no início
- `contexto.json` centraliza dados coletados e estado atual das fases
- O sistema nunca faz a mesma pergunta duas vezes (verifica contexto antes de perguntar)

### RF09 — Execução sequencial das 5 fases
- Fase 1: Diagnóstico (mapeamento de processos e dependências)
- Fase 2: Especialização (redesenho de papéis e responsabilidades)
- Fase 3: Capital Fixo (SOPs + automações priorizadas)
- Fase 4: Incentivos (modelo de metas e reconhecimento)
- Fase 5: Mercado (análise de carteira e posicionamento)
- Cada fase só inicia após aprovação do CEO na fase anterior

### RF10 — CLAUDE.md para Claude Code
- O sistema gera automaticamente um `CLAUDE.md` ao ser inicializado
- Documenta: contexto do projeto, padrões usados, decisões arquiteturais, estado atual

---

## 4. Requisitos Técnicos

### Stack obrigatória
- **Orquestrador:** n8n (self-hosted ou cloud)
- **LLM:** Claude API (claude-sonnet-4-5-20251001 para agentes, claude-haiku-4-5-20251001 para tarefas simples)
- **WhatsApp:** Z-API (webhook de entrada + HTTP request de saída)
  - Docs: https://developer.z-api.io
  - Header obrigatório em todas as requisições: `Client-Token`
- **Banco de dados (estado do agente):** PostgreSQL 62.171.191.4:5432
  - Banco dedicado: `smith_project` (criado automaticamente pelo setup.py)
  - Usuário: configurado via `.env` — nunca hardcoded
- **Armazenamento de documentos:** Google Drive API v3
  - Usado APENAS para documentos legíveis pelo CEO (SOPs, relatórios, mapas)
  - Estado do agente fica exclusivamente no PostgreSQL
- **Variáveis de ambiente:** `.env` com todas as credenciais (nunca hardcoded)

### Padrões de agente
- **Orquestrador:** padrão Multi-Agente com ReAct loop
- **Sub-agentes:** cada um é um sub-workflow n8n separado, ativado por webhook interno
- **Memória:** Google Drive como store persistente (não usar memória volátil do n8n)
- **Autorreflexão:** sub-agente Redator usa 2 chamadas LLM (gerar + revisar) antes de salvar

### Estrutura de arquivos do projeto
```
projeto-smith/
  .env.example
  CLAUDE.md
  tools/
    db_client.py           ← PostgreSQL (estado do agente)
    gdrive_client.py       ← Google Drive (documentos CEO)
    whatsapp_client.py     ← Z-API
    llm_client.py          ← Claude API
    context_manager.py     ← abstração sobre db_client
    sop_template.py
    phase_manager.py
    setup.py               ← inicialização única
    test_flow.py
  prompts/
    orquestrador.md
    entrevistador.md
    mapeador.md
    redator_sops.md
    analista_economico.md
    followup.md
  workflows/
    00-orquestrador.json
    01-onboarding-ceo.json
    02-entrevista-equipe.json
    03-mapeador-processos.json
    04-redator-sops.json
    05-analista-economico.json
    06-followup-semanal.json
    07-fluxo-aprovacao.json
    08-gerenciador-memoria.json
```

### Schema PostgreSQL (banco: smith_project)
```
project_context   ← chave-valor para estado do projeto
messages_log      ← histórico de WhatsApp enviado e recebido
decisions_log     ← decisões do CEO com timestamp
interviews        ← transcrições de entrevistas com equipe
documents         ← SOPs, mapas, relatórios (metadados + conteúdo)
phase_status      ← estado e aprovação de cada fase
```

### Google Drive (documentos para leitura do CEO)
```
iDVL/
  Agente Smith/
    SOPs/
    Mapas de Processo/
    Relatórios de Diagnóstico/
```

---

## 5. Guardrails e Segurança

- Nunca enviar mensagem à equipe sem aprovação prévia do CEO
- Nunca acessar banco Domínio sem variável de ambiente `DOMINIO_DB_ENABLED=true`
- Máximo 3 mensagens WhatsApp por dia ao CEO (exceto aprovações urgentes)
- Timeout de 72h para respostas; após isso, registrar como bloqueio e notificar
- Todas as chamadas LLM com temperatura 0.3 para consistência
- Limite de 10 iterações no ReAct loop do orquestrador por execução

---

## 6. Critérios de Aceite

- [ ] CEO recebe e responde onboarding completo via WhatsApp
- [ ] Sistema salva contexto.json com todas as respostas após onboarding
- [ ] Entrevistas são enviadas automaticamente aos membros da equipe indicados
- [ ] Mapa de processos é gerado e salvo no Google Drive após entrevistas
- [ ] Pelo menos 1 SOP é gerado, revisado internamente e enviado para aprovação
- [ ] Follow-up semanal é enviado automaticamente na sexta-feira
- [ ] Aprovação do CEO via WhatsApp avança a fase corretamente
- [ ] "Ajusta" no WhatsApp re-abre a fase atual sem perder dados
- [ ] Sistema nunca faz a mesma pergunta duas vezes ao CEO
- [ ] Todos os arquivos criados seguem a estrutura de pastas definida

---

## 7. Dependências Externas

- Evolution API v2: https://doc.evolution-api.com/v2/pt/get-started/introduction
- Google Drive API v3: https://developers.google.com/drive/api/reference/rest/v3
- Claude API: https://docs.anthropic.com/en/api/messages
- n8n workflow docs: https://docs.n8n.io/integrations/builtin/core-nodes/

---

## 8. Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| CEO não responder WhatsApp | Média | Follow-up automático em 48h, bloqueio registrado em 72h |
| Evolution API instável | Média | Retry com backoff exponencial (3 tentativas) |
| Google Drive quota excedida | Baixa | Batching de escritas, cache local antes de salvar |
| LLM retornar JSON inválido | Média | Schema validation + retry com instrução de correção |
| Fase avançar sem aprovação | Baixa | Verificação obrigatória de `fase.aprovada === true` antes de trigger |

---

## Metadata (uso interno)
status: ready_for_spec
next_step: spec-generator
generated_at: 2026-03-28
