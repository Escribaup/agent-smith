# Agente Smith — iDVL Gestão 🤖

Bem-vindo ao repositório do **Agente Smith**. Este é um sistema multi-agente construído no n8n que conduz projetos de profissionalização de gestão (focado inicialmente na [iDVL Tecnologia Contábil](https://idvl.com.br/)), interagindo diretamente com os usuários via WhatsApp.

O sistema divide o trabalho complexo em vários agentes especializados (baseado nos ideais de Adam Smith) suportados por um back-end Python FastAPI robusto, banco PostgreSQL dedicado e integrações ágeis.

---

## 🚀 Arquitetura Simplificada

A infraestrutura foi desenhada para subir com um único comando Docker num servidor VPS. Ela provisiona 3 contêineres:
- **n8n (`smith_n8n`)**: Orquestrador das rotinas e comunicações.
- **PostgreSQL (`smith_postgres`)**: Memória transacional e estado do projeto.
- **FastAPI (`smith_api`)**: API Python que envelopa toda a lógica pesada e inteligência do Agente Smith presente na pasta `/tools`.

---

## ⚙️ Implantação Rápida (Deploy na VPS)

O deploy foi automatizado para que **qualquer pessoa possa subir tudo do zero em menos de 5 minutos.** 

### 1. Pré-Requisitos
Você só precisa de uma máquina Linux / VPS (ex: Ubuntu 22.04) com **Git** instalado. 
*(Obs: o script verificará automaticamente se o Docker e Docker Compose estão instalados e instruirá sobre o que fazer se não estiverem).*

Você também vai precisar acessar a sua VPS via SSH. No terminal da sua máquina, digite:
```bash
ssh root@seu-ip
```

### 2. Passo a Passo do Setup

**A. Clone o repositório**
```bash
git clone https://github.com/Escribaup/agent-smith.git
cd agent-smith
```

**B. Dê permissão ao Instalador**
```bash
chmod +x deploy.sh
```

**C. Execute o Instalador**
```bash
./deploy.sh
```

**Opcional - Importação Automática dos Workflows:**
O script tenta importar todos os fluxos da pasta `/workflows` sozinhos para o n8n no final. Para que isso funcione 100%, você deve:
1. Abrir o n8n assim que ele subir (`http://SEU_IP:5678`).
2. Criar a sua conta de admin.
3. Ir em Settings > API > Create API Key.
4. Adicionar essa chave na variável temporária local ou, se o script informou que não importou por falta de chave, importá-los via painel web ou adicionando-a ao seu arquivo `.env` e rodando o comando de script de novo.

---

## 🔑 Credenciais (Tenha em Mãos)

Durante a execução do `./deploy.sh`, ele criará o arquivo `.env` com segurança, porém vai fazer as seguintes perguntas interativas (então tenha essas respostas prontas):

1. **ANTHROPIC_API_KEY**: Chave de uso da API Claude (ex: `sk-ant-xxx`).
2. **ZAPI_INSTANCE_ID** e **ZAPI_TOKEN**: Chaves do gerenciador de disparo [Z-API](https://z-api.io) do seu WhatsApp.
3. **CEO_WHATSAPP**: Telefone administrador inicial apenas em números (Ex: `5541999999999`).
4. **POSTGRES_PASSWORD**: Crie uma senha forte (O postgres inicializa com ela).
5. **Google Drive (OAuth2)**:
   - Acesse [console.cloud.google.com](https://console.cloud.google.com/apis/credentials)
   - Crie uma credencial **ID do cliente OAuth** → Tipo: **Aplicativo para computador**
   - Copie o **Client ID** e **Client Secret** gerados
   - Também anote o **ID da pasta** do Google Drive onde os relatórios serão salvos
   - Durante o deploy, o script pedirá que você faça login na conta Google via URL no terminal

---

## 🚦 O Primeiro Acesso

Terminou o Deploy? Excelente.

1. **Acessar N8N**: Vá em `http://<IP-DA-VPS>:5678/` e confirme se todos os Workflows de 00 a 08 estão listados.
2. **Rodando a Setup da Base (Opcional se auto falhou)**: A API sobe o Banco de dados sozinha, mas se preferir validar abra o `http://<IP-DA-VPS>:8000/docs` e faça o POST no `/setup`.
3. **Iniciando a Gestão**: Para disparar o primeiro agente, ative o *Workflow `00-orquestrador`* no N8N. Ele tem o gatilho de *Webhook* que passa a escutar os WhatsApp recepcionados pelos números atrelados ao dono. Dê um 'Oi'.

---

## Estrutura do Repositório

```text
├── tools/                 # Ferramentas Python que o N8N consulta.
│   ├── api.py             # App FastAPI 
│   ├── setup.py           # Instalador das tabelas 
│   └── *.py               # Clients do DB, Drive, Whatsapp, etc...
├── workflows/             # Arquivos .json exportados do painel N8N.
├── prompts/               # System Prompts injetados para o modelo.
├── docker-compose.yml     # Orquestrador oficial em Docker.
├── Dockerfile             # Containerizer isolado para o FastAPI.
├── deploy.sh              # Magic Script Interativo de Setup.
└── requirements.txt       # Dependências da lógica de I.A do Python.
```

Feito e mantido pela **iDVL Tecnologia Contábil**. 
> *Somos mais que parceiros dos nossos clientes, somos a extensão do sucesso deles.*
