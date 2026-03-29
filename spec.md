# SPEC — Agente Smith: Plano de Implementação Arquivo por Arquivo

> Fonte: `docs/prd.md` | Status: ready_for_code
> Leia este documento inteiro antes de criar qualquer arquivo.
> Implemente na ordem exata das fases abaixo.

---

## FASE 0 — Fundação: Estrutura, Variáveis e CLAUDE.md

### 0.1 `.env.example` (CRIAR)

> ATENÇÃO ao Claude Code: este é o template. O arquivo `.env` real
> nunca deve ser versionado. Adicione `.env` ao `.gitignore` imediatamente.

```
# ─────────────────────────────────────────────
# ANTHROPIC
# ─────────────────────────────────────────────
ANTHROPIC_API_KEY=                        # sk-ant-...

# ─────────────────────────────────────────────
# WHATSAPP — Z-API
# Obtenha em: app.z-api.io → sua instância → Credenciais
# ─────────────────────────────────────────────
ZAPI_INSTANCE_ID=                         # Ex: 3DF...ABC
ZAPI_TOKEN=                               # Token da instância
ZAPI_CLIENT_TOKEN=                        # Client-Token (header obrigatório)
ZAPI_BASE_URL=https://api.z-api.io/instances

CEO_WHATSAPP=5541999999999                # Apenas números, sem @s.whatsapp.net

# ─────────────────────────────────────────────
# GOOGLE DRIVE
# Service Account com permissão na pasta raiz
# ─────────────────────────────────────────────
GOOGLE_SERVICE_ACCOUNT_JSON=              # JSON completo da service account (base64)
GDRIVE_ROOT_FOLDER_ID=                    # ID da pasta "iDVL" no Drive

# ─────────────────────────────────────────────
# POSTGRESQL — Banco dedicado do projeto
# Host: 62.171.191.4  |  Port: 5432
# O banco "smith_project" será criado pelo setup.py
# ─────────────────────────────────────────────
POSTGRES_HOST=62.171.191.4
POSTGRES_PORT=5432
POSTGRES_DB=smith_project                 # Criado automaticamente pelo setup.py
POSTGRES_USER=postgres
POSTGRES_PASSWORD=                        # Preencha com sua senha atual

# ─────────────────────────────────────────────
# N8N
# ─────────────────────────────────────────────
N8N_WEBHOOK_BASE_URL=https://seu-n8n.com/webhook
N8N_API_KEY=                              # Settings → API → Create API Key

# ─────────────────────────────────────────────
# PROJETO (preenchido automaticamente pelo setup.py)
# ─────────────────────────────────────────────
PROJECT_START_DATE=
PROJECT_DB_INITIALIZED=false
```

---

### 0.2 `CLAUDE.md` (CRIAR)
Instrução para o Claude Code: este arquivo descreve o projeto inteiro.

```markdown
# Agente Smith — iDVL Gestão

## O que este projeto faz
Sistema multi-agente n8n que conduz um projeto de profissionalização de gestão
para um escritório contábil (iDVL), operando via WhatsApp com o CEO e equipe.

## Arquitetura (Divisão do Trabalho — Adam Smith)
- Orquestrador: coordena, nunca executa diretamente
- 5 sub-agentes especializados: Entrevistador, Mapeador, Redator SOPs, Analista, Follow-up
- Memória primária: PostgreSQL banco smith_project (62.171.191.4:5432)
- Memória de documentos: Google Drive (SOPs, relatórios, mapas)
- Comunicação: Z-API para WhatsApp

## Padrões usados
- Todos os workflows n8n estão em `workflows/` como JSON exportável
- Todas as ferramentas Python estão em `tools/`
- Todos os system prompts estão em `prompts/` como .md
- Variáveis de ambiente em `.env` (nunca hardcode credenciais)

## Estado atual do projeto
Ver `contexto.json` no Google Drive para fase atual e dados coletados.

## Regras de implementação
1. Nunca hardcode nenhuma credencial
2. Sempre valide JSON retornado pelo LLM antes de salvar
3. Sempre verifique contexto.json antes de fazer qualquer pergunta
4. Toda mensagem WhatsApp ao CEO: máximo 5 linhas, sem markdown
5. Toda aprovação de fase requer `fase.aprovada === true` no contexto
```

---

## FASE 1 — Tools Python (executadas pelos nós n8n)

### 1.1 `tools/context_manager.py` (CRIAR)
Requisito: RF08
Responsabilidade: camada de abstração sobre db_client para o contexto do projeto.
Depende de: `tools/db_client.py`

```python
# Este módulo é um wrapper de conveniência sobre db_client.
# Todo estado do projeto passa por aqui — nunca acesse db_client diretamente
# nos workflows. Isso garante que a troca de storage nunca quebre os workflows.

def get_context() -> dict:
    """
    Retorna contexto completo do projeto como dict.
    Delega para db_client.get_full_context().
    Retorna estrutura vazia com schema padrão se banco ainda não foi populado.
    """

def get(path: str, default=None):
    """
    Lê campo por path pontilhado.
    Exemplo: get("fases.fase1.aprovada", False)
    Delega para db_client.get_context_value().
    """

def set(path: str, value) -> bool:
    """
    Define campo por path pontilhado.
    Exemplo: set("empresa.headcount", 8)
    Delega para db_client.set_context_value().
    """

def already_asked(question_key: str) -> bool:
    """
    Verifica se pergunta já foi feita.
    Delega para db_client.already_asked().
    """

def get_current_phase() -> str:
    """
    Retorna fase atual. Delega para db_client.get_current_phase().
    """

def can_advance() -> bool:
    """
    Verifica se fase atual está aprovada para avançar.
    Lê phase_status da fase atual no banco.
    """
```

---

### 1.2 `tools/gdrive_client.py` (CRIAR)
Requisito: RF04 (SOPs), RF05 (relatórios), RF03 (mapas de processo)
Responsabilidade: armazenamento de documentos legíveis no Google Drive.
NOTA: Google Drive é usado APENAS para documentos que o CEO precisa ler.
Todo o estado do agente fica no PostgreSQL (db_client.py).

```python
# Dependências: google-auth, google-api-python-client

def get_drive_service():
    """Inicializa cliente Drive via service account (base64 do .env)."""

def create_folder(parent_id: str, name: str) -> str:
    """Cria pasta. Idempotente — retorna ID existente se já houver."""

def write_document(parent_id: str, filename: str, content: str) -> str:
    """
    Cria ou atualiza arquivo .md no Drive. Retorna file_id.
    Se arquivo com mesmo nome existir no parent, faz update.
    """

def get_shareable_link(file_id: str) -> str:
    """
    Torna arquivo público (view only) e retorna link.
    Usado para enviar link do SOP ao CEO via WhatsApp.
    """

def setup_document_folders(root_folder_id: str) -> dict:
    """
    Cria pastas de documentos do projeto. Idempotente.
    Retorna: { "sops": folder_id, "relatorios": folder_id, "mapas": folder_id }
    Salva os IDs no PostgreSQL via db_client.set_context_value().
    """
```

---

### 1.3 `tools/whatsapp_client.py` (CRIAR)
Requisito: RF01, RF02, RF06, RF07
Responsabilidade: envio e parsing de mensagens via Z-API.

Documentação Z-API: https://developer.z-api.io/message/send-text

```python
# Dependências: httpx
# Variáveis de ambiente necessárias:
#   ZAPI_INSTANCE_ID, ZAPI_TOKEN, ZAPI_CLIENT_TOKEN,
#   ZAPI_BASE_URL, CEO_WHATSAPP

def _get_zapi_headers() -> dict:
    """
    Retorna headers obrigatórios da Z-API.
    Z-API exige o header 'Client-Token' em TODAS as requisições.
    {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_CLIENT_TOKEN
    }
    """

def send_message(to: str, text: str) -> bool:
    """
    Envia mensagem de texto via Z-API.

    Endpoint: POST {ZAPI_BASE_URL}/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text

    Body:
    {
        "phone": to,   # apenas números: "5541999999999"
        "message": text
    }

    Máximo 4096 chars. Retorna True se status 200.
    Retry 3x com backoff exponencial (1s, 2s, 4s).
    Log de erro se falhar todas as tentativas.
    """

def parse_incoming_webhook(payload: dict) -> dict | None:
    """
    Parseia payload do webhook Z-API.

    Z-API envia webhooks no formato:
    {
        "instanceId": str,
        "messageId": str,
        "phone": "5541999999999",    ← número do remetente
        "fromMe": false,
        "momment": timestamp,
        "type": "ReceivedCallback",
        "chatName": str,
        "text": {
            "message": str           ← texto da mensagem
        }
    }

    Retorna: { "from": str, "text": str, "timestamp": int }
    Retorna None se:
    - fromMe == true (mensagem enviada por nós)
    - type != "ReceivedCallback"
    - Não há campo text.message
    - É mensagem de mídia (image, audio, video, document)
    """

def is_from_ceo(sender: str) -> bool:
    """
    Verifica se remetente é o CEO.
    Compara sender (apenas números) com CEO_WHATSAPP do .env.
    Remove qualquer sufixo @s.whatsapp.net se presente.
    """

def format_message(lines: list[str]) -> str:
    """
    Formata lista de linhas em mensagem WhatsApp.
    Sem markdown, sem asteriscos, sem # headers.
    Máximo 5 linhas. Trunca se necessário com "..."
    Separa linhas com \\n simples.
    """
```

Configuração do webhook Z-API (instrução ao Claude Code — incluir no README):
```
No painel Z-API (app.z-api.io):
Instância → Webhooks → On Message Received
URL: {N8N_WEBHOOK_BASE_URL}/smith/incoming
Marcar: "Mensagens de texto recebidas"
NÃO marcar: áudio, imagem, vídeo, documento (o agente só processa texto)
```

---

### 1.4 `tools/db_client.py` (CRIAR)
Requisito: RF08 (substitui Google Drive como memória primária de estado)
Responsabilidade: toda persistência de estado do projeto no PostgreSQL.

```python
# Dependências: psycopg2-binary, python-dotenv
# Banco: smith_project (criado pelo setup.py)
# Host: lido de POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

def get_connection():
    """
    Retorna conexão psycopg2 usando variáveis de ambiente.
    Usa connection pooling simples (singleton por processo).
    """

def create_schema() -> None:
    """
    Cria todas as tabelas se não existirem (idempotente).
    Chamada obrigatória pelo setup.py na inicialização.

    Tabelas:

    project_context
    ───────────────
    id          SERIAL PRIMARY KEY
    key         TEXT UNIQUE NOT NULL   -- path pontilhado: "fases.fase1.aprovada"
    value       JSONB NOT NULL
    updated_at  TIMESTAMP DEFAULT NOW()

    messages_log
    ────────────
    id          SERIAL PRIMARY KEY
    direction   TEXT NOT NULL          -- 'in' | 'out'
    from_to     TEXT NOT NULL          -- número whatsapp
    text        TEXT NOT NULL
    timestamp   TIMESTAMP DEFAULT NOW()
    processed   BOOLEAN DEFAULT FALSE

    decisions_log
    ─────────────
    id          SERIAL PRIMARY KEY
    phase       TEXT NOT NULL
    decision    TEXT NOT NULL          -- texto livre da decisão
    made_by     TEXT NOT NULL          -- 'ceo' | 'agent'
    timestamp   TIMESTAMP DEFAULT NOW()

    interviews
    ──────────
    id          SERIAL PRIMARY KEY
    person_name TEXT NOT NULL
    phone       TEXT NOT NULL
    phase       TEXT NOT NULL
    questions   JSONB NOT NULL         -- lista de {pergunta, resposta}
    completed   BOOLEAN DEFAULT FALSE
    created_at  TIMESTAMP DEFAULT NOW()

    documents
    ─────────
    id          SERIAL PRIMARY KEY
    type        TEXT NOT NULL          -- 'sop' | 'process_map' | 'diagnostic' | 'report'
    phase       TEXT NOT NULL
    title       TEXT NOT NULL
    content     TEXT NOT NULL          -- markdown
    gdrive_id   TEXT                   -- ID do arquivo no Google Drive (opcional)
    approved    BOOLEAN DEFAULT FALSE
    version     INTEGER DEFAULT 1
    created_at  TIMESTAMP DEFAULT NOW()
    updated_at  TIMESTAMP DEFAULT NOW()

    phase_status
    ────────────
    phase       TEXT PRIMARY KEY       -- 'onboarding' | 'fase1' ... 'fase5'
    started     BOOLEAN DEFAULT FALSE
    approved    BOOLEAN DEFAULT FALSE
    started_at  TIMESTAMP
    approved_at TIMESTAMP
    notes       TEXT
    """

# ── Context (chave-valor flexível) ──────────────────────────

def get_context_value(key: str, default=None):
    """
    Lê valor por key pontilhada do project_context.
    Retorna default se não encontrar. Nunca lança exceção.
    """

def set_context_value(key: str, value) -> bool:
    """
    Upsert de valor no project_context.
    value pode ser qualquer tipo serializável em JSONB.
    Retorna True se sucesso.
    """

def get_full_context() -> dict:
    """
    Retorna todos os valores do project_context como dict aninhado.
    Reconstrói hierarquia a partir de keys pontilhadas.
    """

def already_asked(question_key: str) -> bool:
    """
    Verifica se pergunta já foi feita e respondida.
    Chave: "onboarding.q1", "entrevista.joao.q3"
    Consulta project_context onde key = question_key e value != null.
    """

# ── Mensagens ────────────────────────────────────────────────

def log_message(direction: str, from_to: str, text: str) -> int:
    """
    Registra mensagem no messages_log. Retorna ID.
    direction: 'in' (recebida) | 'out' (enviada)
    """

def mark_message_processed(message_id: int) -> None:
    """Marca mensagem como processada."""

def get_pending_messages() -> list[dict]:
    """Retorna mensagens recebidas não processadas."""

# ── Decisões ─────────────────────────────────────────────────

def log_decision(phase: str, decision: str, made_by: str) -> None:
    """Registra decisão no decisions_log com timestamp."""

def get_decisions_log(phase: str = None) -> list[dict]:
    """Retorna log de decisões. Se phase=None, retorna tudo."""

# ── Entrevistas ──────────────────────────────────────────────

def save_interview_answer(person_name: str, phone: str,
                          phase: str, question: str, answer: str) -> None:
    """Adiciona par pergunta/resposta à entrevista da pessoa."""

def mark_interview_complete(person_name: str, phase: str) -> None:
    """Marca entrevista de uma pessoa como concluída."""

def get_interview(person_name: str, phase: str) -> dict | None:
    """Retorna entrevista completa de uma pessoa."""

def get_all_interviews(phase: str) -> list[dict]:
    """Retorna todas as entrevistas de uma fase."""

# ── Documentos ───────────────────────────────────────────────

def save_document(doc_type: str, phase: str, title: str,
                  content: str, gdrive_id: str = None) -> int:
    """Salva documento. Retorna ID."""

def approve_document(doc_id: int) -> None:
    """Marca documento como aprovado."""

def get_documents(phase: str, doc_type: str = None) -> list[dict]:
    """Retorna documentos de uma fase, opcionalmente filtrados por tipo."""

def update_document(doc_id: int, content: str) -> None:
    """Atualiza conteúdo do documento, incrementa version."""

# ── Fases ────────────────────────────────────────────────────

def get_phase_status(phase: str) -> dict:
    """Retorna status completo de uma fase."""

def start_phase(phase: str) -> None:
    """Marca fase como iniciada com timestamp."""

def approve_phase(phase: str, notes: str = None) -> None:
    """Marca fase como aprovada com timestamp e notas opcionais."""

def get_current_phase() -> str:
    """
    Retorna fase atual do projeto.
    Lógica: última fase com started=true e approved=false.
    Se todas aprovadas: retorna 'concluido'.
    Se nenhuma iniciada: retorna 'onboarding'.
    """
```
Requisito: todos os RFs com LLM
Responsabilidade: chamadas à Claude API com controle de schema.

```python
# Dependências: anthropic

def call_claude(
    system_prompt: str,
    user_message: str,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 2048,
    temperature: float = 0.3,
    expect_json: bool = False
) -> str | dict:
    """
    Chamada à API Claude.
    Se expect_json=True: valida que resposta é JSON válido.
    Se JSON inválido: retry 1x com instrução "responda APENAS JSON válido".
    Se falhar novamente: lança ValueError com resposta bruta.
    Modelo padrão: haiku (rápido). Use sonnet para análises complexas.
    """

def call_claude_with_reflection(
    system_prompt: str,
    user_message: str,
    critique_prompt: str
) -> str:
    """
    Chamada com autorreflexão (padrão Redator SOPs).
    1. Gera resposta inicial
    2. Usa critique_prompt para revisar
    3. Gera versão final
    Sempre usa claude-sonnet-4-5-20251001.
    """
```

---

### 1.5 `tools/sop_template.py` (CRIAR)
Requisito: RF04
Responsabilidade: template padronizado para SOPs.

```python
def render_sop(data: dict) -> str:
    """
    Renderiza SOP em markdown a partir de dict.

    Campos obrigatórios do dict:
    - processo: str
    - objetivo: str
    - responsavel: str
    - inputs: list[str]
    - passos: list[{ "numero": int, "acao": str, "quem": str, "tempo": str }]
    - criterio_qualidade: str
    - se_travar: str
    - versao: str (ex: "v1")
    - data: str

    Retorna markdown formatado.
    """

def extract_sop_data_from_interview(interview_text: str) -> dict:
    """
    Usa LLM para extrair campos do SOP a partir de entrevista livre.
    Retorna dict compatível com render_sop().
    """
```

---

### 1.6 `tools/phase_manager.py` (CRIAR)
Requisito: RF09
Responsabilidade: controle de estado e transição entre fases.

```python
PHASE_ORDER = ["onboarding", "fase1", "fase2", "fase3", "fase4", "fase5", "concluido"]

PHASE_LABELS = {
    "fase1": "Fase 1 — Diagnóstico",
    "fase2": "Fase 2 — Especialização",
    "fase3": "Fase 3 — Capital Fixo",
    "fase4": "Fase 4 — Incentivos",
    "fase5": "Fase 5 — Mercado"
}

def get_current_phase(context: dict) -> str:
    """Retorna fase atual do projeto."""

def can_advance(context: dict) -> bool:
    """Verifica se fase atual está aprovada e pode avançar."""

def advance_phase(context: dict) -> dict:
    """
    Avança para próxima fase. Atualiza contexto.
    Nunca avança sem can_advance() == True.
    """

def get_phase_summary(context: dict, phase: str) -> str:
    """
    Retorna resumo formatado de uma fase para o relatório semanal.
    """

def is_blocked(context: dict, hours: int = 48) -> bool:
    """
    Verifica se há bloqueio ativo há mais de `hours` horas.
    """
```

---

## FASE 2 — System Prompts

### 2.1 `prompts/orquestrador.md` (CRIAR)
Requisito: RF01 a RF09

```
Você é o Agente Smith, orquestrador do projeto de profissionalização da gestão
da iDVL Tecnologia Contábil.

IDENTIDADE: Você coordena — nunca executa. Você delega para sub-agentes
especializados e interpreta os resultados. Pense como um COO que contrata
especialistas e acompanha o trabalho deles.

PRINCÍPIO FUNDADOR: Você mesmo é organizado pela divisão do trabalho de Adam
Smith. Cada sub-agente tem uma função única. Você garante que o produto de cada
um vire insumo para o próximo.

COMUNICAÇÃO COM CEO:
- Apenas via WhatsApp
- Máximo 5 linhas por mensagem
- Sem markdown, sem asteriscos, sem headers
- Sempre termine com ação clara ou pergunta objetiva
- Nunca faça a mesma pergunta duas vezes (verifique contexto antes)

FLUXO DE DECISÃO:
1. Leia o contexto.json completo
2. Identifique a fase atual e o próximo passo
3. Verifique se há bloqueios ativos
4. Execute a ação correspondente via sub-agente correto
5. Registre resultado no contexto

GUARDRAILS:
- Nunca envie mensagem à equipe sem aprovação do CEO
- Nunca avance de fase sem aprovação explícita (fase.aprovada === true)
- Se CEO responder "Ajusta", pergunte o que mudar antes de reprocessar
- Registre TODAS as decisões do CEO em log-decisoes.md

Responda sempre em JSON com o seguinte schema:
{
  "acao": "enviar_whatsapp | acionar_subagente | aguardar | registrar_log",
  "subagente": "entrevistador | mapeador | redator | analista | followup | null",
  "mensagem": "texto para WhatsApp ou null",
  "destinatario": "ceo | nome_colaborador | null",
  "atualizacao_contexto": {} ou null,
  "razao": "explicação da decisão em 1 linha"
}
```

---

### 2.2 `prompts/entrevistador.md` (CRIAR)
Requisito: RF01, RF02

```
Você é o sub-agente Entrevistador do Agente Smith.

FUNÇÃO ÚNICA: Coletar informações via WhatsApp. Você não analisa, não
interpreta, não diagnostica. Você pergunta, escuta e organiza.

ROTEIRO DE ONBOARDING (CEO — 9 perguntas em 3 blocos):

Bloco 1 — Contexto do negócio:
Q1: "Quantas pessoas trabalham na iDVL hoje (sócios + equipe)?"
Q2: "Quais são os 3 serviços que mais geram receita?"
Q3: "Qual é o maior gargalo operacional que você sente hoje?"

Bloco 2 — Pessoas e processos:
Q4: "Quais pessoas devo entrevistar para mapear os processos? Me manda nome e função."
Q5: "Qual processo você mais teme que trave se uma pessoa-chave sair?"
Q6: "Existe algum processo documentado hoje? Se sim, qual?"

Bloco 3 — Expectativas:
Q7: "Qual resultado tornaria este projeto um sucesso para você em 90 dias?"
Q8: "Há alguma área que você quer que eu NÃO mexa por enquanto? Por quê?"
Q9: "Qual é seu nível de disponibilidade para responder perguntas?"

ROTEIRO DE ENTREVISTA (equipe):
Q1: "O que você faz no dia a dia? Me conta as principais tarefas."
Q2: "Qual tarefa consome mais tempo da sua semana?"
Q3: "O que mais te trava ou atrasa no trabalho?"
Q4: "Se você saísse amanhã, o que travaria sem você?"
Q5: "Existe algum processo que você faz que acha que poderia ser mais fácil?"

REGRAS:
- Uma pergunta por mensagem
- Aguarde resposta antes de enviar a próxima
- Se resposta for vaga, peça um exemplo concreto (apenas 1 vez por pergunta)
- Salve cada resposta imediatamente no contexto com a chave correta

Responda em JSON:
{
  "proxima_pergunta": "texto da pergunta ou null se concluído",
  "chave_contexto": "caminho pontilhado para salvar a resposta",
  "valor_para_salvar": "resposta parseada",
  "concluido": true | false
}
```

---

### 2.3 `prompts/mapeador.md` (CRIAR)
Requisito: RF03

```
Você é o sub-agente Mapeador de Processos do Agente Smith.

FUNÇÃO ÚNICA: Transformar respostas de entrevistas em mapas estruturados de
processo. Você não prescreve mudanças — apenas descreve a realidade atual.

INPUT: Transcrições de entrevistas salvas em /entrevistas/

OUTPUT para cada processo identificado:
{
  "processo": "nome claro e direto",
  "area": "fiscal | folha | contabil | atendimento | honorarios | outro",
  "responsavel_atual": "nome",
  "etapas": [
    {
      "ordem": 1,
      "descricao": "o que é feito",
      "executor": "quem faz",
      "tempo_estimado": "X horas/semana",
      "ferramenta": "sistema ou planilha usada"
    }
  ],
  "gargalo_principal": "descrição do ponto de travamento",
  "dependencia_pessoa": true | false,
  "nome_pessoa_critica": "nome ou null",
  "trabalho_produtivo": true,
  "observacoes": "qualquer detalhe relevante"
}

CLASSIFICAÇÃO Smith (inclua sempre):
- trabalho_produtivo: o processo entrega valor direto ao cliente? (true/false)
- dependencia_pessoa: o processo trava se esta pessoa sair? (true/false)

Gere um JSON array com todos os processos mapeados.
Inclua APENAS o que foi dito nas entrevistas. Não invente.
```

---

### 2.4 `prompts/redator_sops.md` (CRIAR)
Requisito: RF04

```
Você é o sub-agente Redator de SOPs do Agente Smith.

FUNÇÃO ÚNICA: Escrever Procedimentos Operacionais Padrão claros, diretos e
executáveis. Qualquer colaborador treinado deve conseguir seguir o SOP sem
perguntar ao sócio.

INPUT: mapa de processo gerado pelo Mapeador

CRITÉRIO DE QUALIDADE: O SOP é bom quando um novo colaborador consegue
executar o processo no primeiro dia com apenas este documento como guia.

PROCESSO DE AUTORREFLEXÃO (obrigatório antes de finalizar):
1. Escreva o SOP completo
2. Releia como se fosse um colaborador novo
3. Pergunte: "Há algum passo onde eu ficaria travado?"
4. Corrija qualquer ambiguidade identificada
5. Só então finalize

FORMATO OBRIGATÓRIO DO SOP:
# [Nome do Processo] — SOP v{n}

## Objetivo
[1-2 frases: o que este processo entrega e para quem]

## Responsável
[Cargo/função — não nome de pessoa]

## Quando executar
[Gatilho: frequência, prazo ou evento que dispara]

## Inputs necessários
- [O que precisa estar pronto antes de começar]

## Passo a passo
1. [Ação concreta] — [quem] — [quanto tempo]
2. ...

## Critério de qualidade
[Como saber que foi feito corretamente]

## O que fazer se travar
- Se [problema X]: [ação Y]
- Se [problema Z]: contatar [cargo/função]

## Histórico de versões
| Versão | Data | Alteração |
```

---

### 2.5 `prompts/analista_economico.md` (CRIAR)
Requisito: RF05

```
Você é o sub-agente Analista Econômico do Agente Smith.

FUNÇÃO ÚNICA: Aplicar os princípios de Adam Smith para diagnosticar cada fase
do projeto e gerar recomendações fundamentadas.

PRINCÍPIOS QUE VOCÊ APLICA:

1. Divisão do Trabalho (Livro I, Cap. I)
   Sinal de problema: mesma pessoa faz tudo do início ao fim
   Pergunta diagnóstica: quais etapas poderiam ser especializadas?

2. Capital Fixo x Circulante (Livro II, Cap. I)
   Sinal de problema: mais investimento em pessoas do que em sistemas
   Pergunta diagnóstica: o que poderia ser automatizado antes de contratar?

3. Trabalho Produtivo x Improdutivo (Livro II, Cap. III)
   Sinal de problema: tempo gasto em atividades que não geram entregável
   Pergunta diagnóstica: esta atividade gera algo que o cliente paga?

4. Incentivos e Mão Invisível (Livro IV)
   Sinal de problema: colaborador não sabe o que precisa fazer para ser reconhecido
   Pergunta diagnóstica: o interesse individual está alinhado ao resultado coletivo?

5. Extensão do Mercado (Livro I, Cap. III)
   Sinal de problema: especialização maior do que o mercado atual suporta
   Pergunta diagnóstica: há demanda suficiente para absorver a capacidade criada?

OUTPUT por fase:
{
  "fase": "fase1 | fase2 | fase3 | fase4 | fase5",
  "achados": [
    {
      "tipo": "problema | oportunidade",
      "descricao": "o que foi identificado",
      "principio_smith": "nome do princípio",
      "evidencia": "dado ou fato da entrevista que sustenta",
      "recomendacao": "ação concreta",
      "trade_offs": ["vantagem", "desvantagem"]
    }
  ],
  "diagnostico_geral": "parágrafo síntese em linguagem de negócio",
  "prioridade_acao": "o que fazer primeiro e por quê"
}
```

---

### 2.6 `prompts/followup.md` (CRIAR)
Requisito: RF06

```
Você é o sub-agente de Follow-up do Agente Smith.

FUNÇÃO ÚNICA: Manter o projeto em movimento. Você monitora prazos, cobra
pendências e mantém o CEO informado sem sobrecarregá-lo.

RELATÓRIO SEMANAL (toda sexta às 8h):
Formato para WhatsApp (máximo 5 linhas, sem markdown):

"Resumo semanal — Smith
Concluído: [item mais importante da semana]
Pendente: [item mais urgente]
Precisa de você: [decisão ou informação necessária]"

ALERTA DE BLOQUEIO (quando tarefa atrasa 48h+):
"Alerta: [descrição do bloqueio em 1 linha]
Impacto: [consequência se não resolver]
O que você prefere? Aguardar mais 24h ou seguir sem essa info?"

COBRANÇA GENTIL (quando CEO não responde em 48h):
"Oi Julio, tudo bem? Quando puder, preciso da sua resposta sobre:
[pergunta original resumida em 1 linha]"

REGRAS:
- Máximo 3 mensagens por dia ao CEO
- Nunca envie 2 alertas seguidos sem pelo menos 4h de intervalo
- Se CEO pedir para pausar o projeto, respeite e registre no log
- Registre TUDO em log-decisoes.md com timestamp

Responda em JSON:
{
  "tipo_mensagem": "relatorio_semanal | alerta_bloqueio | cobranca | nenhuma",
  "mensagem": "texto formatado para WhatsApp ou null",
  "registrar_log": true | false,
  "entrada_log": "texto para o log ou null"
}
```

---

## FASE 3 — Workflows n8n (JSON exportável)

> Instrução ao Claude Code: para cada workflow abaixo, gere o JSON completo
> compatível com n8n v1.x. Use o padrão de nodes descrito.
> Todos os credentials são referenciados por nome — nunca por valor.

---

### 3.1 `workflows/00-orquestrador.json` (CRIAR)
Requisito: RF01 a RF09

Nodes obrigatórios (nesta ordem):
```
1. Webhook (POST /webhook/smith/incoming)
   - Recebe mensagens do WhatsApp (Evolution API webhook)
   - Recebe triggers internos de sub-workflows

2. Function: parse-and-route
   - Lê payload recebido
   - Identifica tipo: whatsapp_message | internal_trigger
   - Extrai: sender, text, trigger_type

3. HTTP Request: read-context
   - Chama tools/context_manager.py via Python node ou HTTP
   - Retorna contexto.json completo

4. AI Agent (Claude Sonnet)
   - System prompt: conteúdo de prompts/orquestrador.md
   - Input: contexto + mensagem recebida
   - Output: JSON com acao, subagente, mensagem, atualizacao_contexto

5. Switch: route-action
   - enviar_whatsapp → Node 6
   - acionar_subagente → Node 7
   - aguardar → Node 9
   - registrar_log → Node 8

6. HTTP Request: send-whatsapp
   - Chama Evolution API /message/sendText
   - Headers: apikey do .env

7. Execute Workflow: call-subagent
   - Switch interno por subagente:
     - entrevistador → workflows/01-onboarding-ceo.json
     - mapeador → workflows/03-mapeador-processos.json
     - redator → workflows/04-redator-sops.json
     - analista → workflows/05-analista-economico.json
     - followup → workflows/06-followup-semanal.json

8. Function: save-context
   - Aplica atualizacao_contexto ao contexto atual
   - Salva via gdrive_client.py

9. NoOp: aguardar
   - Apenas registra estado "aguardando resposta"

10. Function: log-decision
    - Appenda entrada no log-decisoes.md com timestamp
```

---

### 3.2 `workflows/01-onboarding-ceo.json` (CRIAR)
Requisito: RF01

Nodes obrigatórios:
```
1. Execute Workflow Trigger (chamado pelo orquestrador)

2. Function: check-onboarding-progress
   - Lê contexto.json
   - Identifica qual pergunta enviar a seguir (already_asked check)
   - Se todas respondidas: marca onboarding.concluido = true

3. AI Agent (Claude Haiku)
   - System prompt: prompts/entrevistador.md
   - Input: contexto atual + resposta mais recente do CEO
   - Output: proxima_pergunta, chave_contexto, valor_para_salvar, concluido

4. HTTP Request: send-whatsapp-question
   - Envia próxima pergunta ao CEO

5. Function: save-answer
   - Salva resposta no caminho correto do contexto

6. IF: onboarding-completo
   - Se concluido == true: dispara trigger para Fase 1
   - Se não: aguarda próxima resposta via webhook
```

---

### 3.3 `workflows/02-entrevista-equipe.json` (CRIAR)
Requisito: RF02

Nodes obrigatórios:
```
1. Execute Workflow Trigger

2. Function: get-next-interviewee
   - Lê lista de equipe do contexto
   - Retorna primeiro membro com entrevistado == false

3. HTTP Request: send-intro-message
   - Envia mensagem de apresentação ao colaborador
   - "Olá [nome], sou o assistente da iDVL. O Julio pediu que eu conversasse
     com você sobre seu trabalho. São 5 perguntas rápidas. Pode ser agora?"

4. Aguarda confirmação via webhook

5. AI Agent (Claude Haiku)
   - System prompt: prompts/entrevistador.md (roteiro de equipe)
   - Loop: envia pergunta → aguarda resposta → próxima pergunta

6. Function: save-interview
   - Salva transcrição completa em /entrevistas/{nome}-{data}.json
   - Marca colaborador como entrevistado no contexto

7. IF: todos-entrevistados
   - Se sim: notifica orquestrador para acionar Mapeador
```

---

### 3.4 `workflows/03-mapeador-processos.json` (CRIAR)
Requisito: RF03

Nodes obrigatórios:
```
1. Execute Workflow Trigger

2. HTTP Request: load-all-interviews
   - Carrega todos os JSONs de /entrevistas/ do Google Drive

3. AI Agent (Claude Sonnet)
   - System prompt: prompts/mapeador.md
   - Input: todas as transcrições concatenadas
   - Output: JSON array de processos mapeados

4. Function: validate-process-map
   - Valida schema de cada processo
   - Sinaliza processos com dependencia_pessoa == true

5. HTTP Request: save-process-map
   - Salva fase-1-mapa-processos.json no Google Drive

6. HTTP Request: send-approval-request
   - Envia ao CEO via WhatsApp:
     "Mapeei X processos da iDVL. Salvei o relatório no Drive.
      Antes de avançar: você quer revisar agora ou posso seguir?
      Responda: Revisar | Seguir"

7. Aguarda resposta do CEO via webhook
```

---

### 3.5 `workflows/04-redator-sops.json` (CRIAR)
Requisito: RF04

Nodes obrigatórios:
```
1. Execute Workflow Trigger
   - Recebe: { processo: objeto de processo do mapa }

2. AI Agent com Reflexão (Claude Sonnet — 2 chamadas)
   Chamada 1: gera SOP inicial
   - System prompt: prompts/redator_sops.md
   - Input: objeto processo + template

   Chamada 2: revisão crítica
   - System prompt: "Você é um revisor de SOPs. Identifique:
     (1) Passos ambíguos, (2) Passos que faltam, (3) Linguagem confusa.
     Retorne o SOP corrigido."
   - Input: SOP gerado na chamada 1

3. Function: render-final-sop
   - Aplica render_sop() do sop_template.py
   - Valida que todos os campos obrigatórios estão presentes

4. HTTP Request: save-sop
   - Salva /sops/{nome-processo}-v1.md no Google Drive

5. HTTP Request: notify-ceo
   - "SOP criado: [nome do processo]
     Salvei no Drive para sua revisão.
     Responda OK para aprovar ou Ajusta para modificar."

6. IF: ceo-approved
   - OK: marca processo como documentado no contexto
   - Ajusta: envia pergunta "O que devo ajustar no SOP?"
             Reprocessa com feedback
```

---

### 3.6 `workflows/05-analista-economico.json` (CRIAR)
Requisito: RF05

Nodes obrigatórios:
```
1. Execute Workflow Trigger
   - Recebe: { fase: "fase1" | "fase2" | ... }

2. Function: load-phase-data
   - Carrega todos os artefatos da fase do Google Drive
   - Mapa de processos, entrevistas, SOPs aprovados

3. AI Agent (Claude Sonnet)
   - System prompt: prompts/analista_economico.md
   - Input: artefatos da fase + contexto do projeto
   - Output: JSON com achados e diagnóstico

4. Function: render-diagnostic-report
   - Converte JSON em relatório .md legível
   - Inclui seção "Princípios Smith Aplicados"

5. HTTP Request: save-report
   - Salva /relatorios/diagnostico-fase-{n}.md no Google Drive

6. HTTP Request: send-summary-to-ceo
   - Envia resumo do diagnóstico (máximo 5 linhas) via WhatsApp
```

---

### 3.7 `workflows/06-followup-semanal.json` (CRIAR)
Requisito: RF06

Nodes obrigatórios:
```
1. Schedule Trigger: toda sexta-feira às 8h (cron: 0 8 * * 5)

2. HTTP Request: load-context
   - Carrega contexto.json atual

3. Function: check-blockers
   - Verifica bloqueios ativos há mais de 48h
   - Se sim: muda tipo_mensagem para "alerta_bloqueio"

4. AI Agent (Claude Haiku)
   - System prompt: prompts/followup.md
   - Input: contexto atual + bloqueios + última semana de log
   - Output: tipo_mensagem, mensagem, registrar_log, entrada_log

5. HTTP Request: send-whatsapp
   - Envia mensagem formatada ao CEO

6. Function: append-to-log
   - Adiciona entrada no log-decisoes.md
```

---

### 3.8 `workflows/07-fluxo-aprovacao.json` (CRIAR)
Requisito: RF07

Nodes obrigatórios:
```
1. Execute Workflow Trigger
   - Recebe: { fase: str, entregavel_url: str, mensagem_ceo: str }

2. HTTP Request: send-approval-request
   - Envia mensagem de aprovação formatada ao CEO

3. Webhook: wait-for-response
   - Aguarda resposta com timeout de 72h
   - Timeout: registra bloqueio no contexto e notifica

4. Function: parse-approval-response
   - "ok" | "OK" | "sim" | "pode" → aprovado = true
   - "ajusta" | "Ajusta" | "muda" → aprovado = false, solicita feedback
   - Qualquer outra coisa → envia "Pode responder OK para aprovar ou Ajusta para modificar"

5. IF: aprovado
   - true: atualiza fase.aprovada = true no contexto, notifica orquestrador
   - false: envia pergunta de feedback, aguarda, retorna para sub-agente com feedback
```

---

### 3.9 `workflows/08-gerenciador-memoria.json` (CRIAR)
Requisito: RF08

Nodes obrigatórios:
```
1. Execute Workflow Trigger (chamado por qualquer outro workflow)
   - Recebe: { operacao: "read" | "write" | "append_log", payload: any }

2. Switch: route-operation

3a. [read] HTTP Request: load-from-gdrive
   - Usa gdrive_client.py para ler arquivo solicitado
   - Retorna conteúdo

3b. [write] HTTP Request: save-to-gdrive
   - Usa gdrive_client.py para escrever/atualizar arquivo
   - Idempotente: não duplica arquivo existente

3c. [append_log] Function: append-log-entry
   - Formata: "[ {timestamp} ] {entrada}"
   - Appenda no log-decisoes.md existente

4. Function: return-result
   - Retorna { sucesso: bool, dados: any, erro: str | null }
```

---

## FASE 4 — Script de Setup Inicial

### 4.1 `tools/setup.py` (CRIAR)
Requisito: RF08, RF10

```python
"""
Execute este script UMA VEZ para inicializar o projeto.
Uso: python tools/setup.py

O que faz:
1. Valida que todas as variáveis de ambiente obrigatórias estão presentes
2. Conecta ao PostgreSQL e cria o banco smith_project se não existir
3. Cria todas as tabelas via db_client.create_schema()
4. Popula phase_status com as 6 fases (onboarding + fase1 a fase5)
5. Cria pastas de documentos no Google Drive
6. Salva folder_ids do Drive no PostgreSQL
7. Marca PROJECT_DB_INITIALIZED=true no .env
8. Testa conexão com Z-API (envia mensagem de teste ao CEO)
9. Imprime resumo completo do setup

IMPORTANTE: Este script cria o banco smith_project automaticamente.
O usuário postgres precisa ter permissão CREATE DATABASE no servidor.
"""

REQUIRED_ENV_VARS = [
    "ANTHROPIC_API_KEY",
    "ZAPI_INSTANCE_ID",
    "ZAPI_TOKEN",
    "ZAPI_CLIENT_TOKEN",
    "ZAPI_BASE_URL",
    "CEO_WHATSAPP",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "GDRIVE_ROOT_FOLDER_ID",
    "N8N_WEBHOOK_BASE_URL"
]

def validate_env() -> list[str]:
    """Retorna lista de variáveis faltando. Lista vazia = OK."""

def create_database_if_not_exists() -> bool:
    """
    Conecta ao PostgreSQL como postgres no banco 'postgres' (padrão).
    Verifica se smith_project existe. Se não: CREATE DATABASE smith_project.
    Retorna True se banco já existia ou foi criado com sucesso.
    """

def initialize_phases() -> None:
    """
    Insere registros iniciais na tabela phase_status para todas as fases.
    Idempotente — usa INSERT ... ON CONFLICT DO NOTHING.
    Fases: onboarding, fase1, fase2, fase3, fase4, fase5
    """

def test_whatsapp_connection() -> bool:
    """
    Envia mensagem de teste ao CEO:
    "Agente Smith ativado. Setup concluido. Aguarde o onboarding."
    Retorna True se mensagem enviada com sucesso.
    """

def print_setup_summary(results: dict) -> None:
    """
    Imprime tabela com status de cada etapa do setup.
    Inclui: PostgreSQL OK/FAIL, tabelas criadas, Drive OK/FAIL, WhatsApp OK/FAIL
    """

if __name__ == "__main__":
    print("=== Setup Agente Smith ===")
    # 1. Valida .env
    # 2. Cria banco
    # 3. Cria schema
    # 4. Inicializa fases
    # 5. Setup Drive
    # 6. Testa WhatsApp
    # 7. Imprime resumo
```

---

## FASE 5 — Testes

### 5.1 `tools/test_flow.py` (CRIAR)
Responsabilidade: simular fluxo completo sem WhatsApp real.

```python
"""
Simula o fluxo de onboarding completo localmente.
Uso: python tools/test_flow.py

Substitui WhatsApp por input() do terminal.
Verifica se contexto.json é atualizado corretamente a cada resposta.
"""

def simulate_onboarding(mock_responses: list[str]) -> dict: ...
def assert_context_schema(context: dict) -> bool: ...
def run_full_simulation() -> None: ...
```

---

## Ordem de Implementação (para o Claude Code)

```
FASE 0 — Fundação
  1.  .env.example
  2.  CLAUDE.md

FASE 1 — Tools (ordem obrigatória — dependências em cascata)
  3.  tools/db_client.py          ← sem dependências, base de tudo
  4.  tools/gdrive_client.py      ← independente do db_client
  5.  tools/whatsapp_client.py    ← independente
  6.  tools/llm_client.py         ← independente
  7.  tools/context_manager.py    ← depende de db_client
  8.  tools/sop_template.py       ← depende de llm_client
  9.  tools/phase_manager.py      ← depende de db_client e context_manager
  10. tools/setup.py              ← depende de todos acima

FASE 2 — Prompts
  11. prompts/orquestrador.md
  12. prompts/entrevistador.md
  13. prompts/mapeador.md
  14. prompts/redator_sops.md
  15. prompts/analista_economico.md
  16. prompts/followup.md

FASE 3 — Workflows n8n (do mais simples ao mais complexo)
  17. workflows/08-gerenciador-memoria.json
  18. workflows/07-fluxo-aprovacao.json
  19. workflows/01-onboarding-ceo.json
  20. workflows/02-entrevista-equipe.json
  21. workflows/03-mapeador-processos.json
  22. workflows/04-redator-sops.json
  23. workflows/05-analista-economico.json
  24. workflows/06-followup-semanal.json
  25. workflows/00-orquestrador.json   ← último, depende de todos

FASE 4 — Setup e Testes
  26. tools/test_flow.py
```

---

## Metadata (uso interno)
status: ready_for_code
next_step: code-generator
source_prd: docs/prd.md
generated_at: 2026-03-28
total_files: 20
implementation_phases: 5
