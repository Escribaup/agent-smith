#!/bin/bash

# =============================================
# Instalador: Agente Smith (VPS & n8n)
# Uso: ./deploy.sh              (instalação nova)
#      ./deploy.sh --reconfig    (corrigir variáveis)
# =============================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─────────────────────────────────
# Variáveis coletadas (array associativo simulado)
# ─────────────────────────────────
declare -A ENV_VALS

# Função: perguntar com validação
ask() {
    local KEY="$1"
    local LABEL="$2"
    local DEFAULT="$3"
    local REQUIRED="${4:-false}"
    local INPUT=""

    while true; do
        if [ -n "$DEFAULT" ]; then
            read -p "  $LABEL [$DEFAULT]: " INPUT
            INPUT="${INPUT:-$DEFAULT}"
        else
            read -p "  $LABEL: " INPUT
        fi

        if [ "$REQUIRED" == "true" ] && [ -z "$INPUT" ]; then
            echo -e "  ${RED}⚠ Campo obrigatório. Tente novamente.${NC}"
            continue
        fi
        break
    done

    ENV_VALS["$KEY"]="$INPUT"
}

# Função: escrever .env a partir das variáveis coletadas
write_env() {
    cat > .env << EOF
# Gerado automaticamente pelo deploy.sh em $(date '+%Y-%m-%d %H:%M:%S')

# ANTHROPIC
ANTHROPIC_API_KEY=${ENV_VALS[ANTHROPIC_API_KEY]}

# WHATSAPP — Z-API
ZAPI_INSTANCE_ID=${ENV_VALS[ZAPI_INSTANCE_ID]}
ZAPI_TOKEN=${ENV_VALS[ZAPI_TOKEN]}
ZAPI_CLIENT_TOKEN=${ENV_VALS[ZAPI_CLIENT_TOKEN]}
ZAPI_BASE_URL=https://api.z-api.io/instances
CEO_WHATSAPP=${ENV_VALS[CEO_WHATSAPP]}

# GOOGLE DRIVE — OAuth2
GOOGLE_CLIENT_ID=${ENV_VALS[GOOGLE_CLIENT_ID]}
GOOGLE_CLIENT_SECRET=${ENV_VALS[GOOGLE_CLIENT_SECRET]}
GDRIVE_ROOT_FOLDER_ID=${ENV_VALS[GDRIVE_ROOT_FOLDER_ID]}

# POSTGRESQL
POSTGRES_HOST=${ENV_VALS[POSTGRES_HOST]}
POSTGRES_PORT=${ENV_VALS[POSTGRES_PORT]}
POSTGRES_DB=${ENV_VALS[POSTGRES_DB]}
POSTGRES_USER=${ENV_VALS[POSTGRES_USER]}
POSTGRES_PASSWORD=${ENV_VALS[POSTGRES_PASSWORD]}

# N8N
N8N_BASE_URL=${ENV_VALS[N8N_BASE_URL]}
N8N_WEBHOOK_BASE_URL=${ENV_VALS[N8N_WEBHOOK_BASE_URL]}
N8N_API_KEY=${ENV_VALS[N8N_API_KEY]}

# PROJETO
PROJECT_START_DATE=$(date '+%Y-%m-%d')
PROJECT_DB_INITIALIZED=false
EOF
    echo -e "${GREEN}✔ Arquivo .env salvo com sucesso.${NC}"
}

# Função: carregar .env existente para as variáveis
load_existing_env() {
    if [ -f .env ]; then
        while IFS='=' read -r key value; do
            # Ignora comentários e linhas vazias
            [[ "$key" =~ ^#.*$ ]] && continue
            [[ -z "$key" ]] && continue
            key=$(echo "$key" | xargs) # trim
            ENV_VALS["$key"]="$value"
        done < .env
    fi
}

# Função: mostrar resumo e pedir confirmação
show_summary() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║        RESUMO DAS CONFIGURAÇÕES              ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Anthropic:${NC}    ${ENV_VALS[ANTHROPIC_API_KEY]:0:20}..."
    echo -e "${CYAN}Z-API ID:${NC}     ${ENV_VALS[ZAPI_INSTANCE_ID]}"
    echo -e "${CYAN}CEO WhatsApp:${NC} ${ENV_VALS[CEO_WHATSAPP]}"
    echo ""
    echo -e "${CYAN}Postgres:${NC}     ${ENV_VALS[POSTGRES_USER]}@${ENV_VALS[POSTGRES_HOST]}:${ENV_VALS[POSTGRES_PORT]}/${ENV_VALS[POSTGRES_DB]}"
    echo -e "${CYAN}Postgres PWD:${NC} ********"
    echo ""
    echo -e "${CYAN}Google ID:${NC}    ${ENV_VALS[GOOGLE_CLIENT_ID]:0:30}..."
    echo -e "${CYAN}GDrive Root:${NC}  ${ENV_VALS[GDRIVE_ROOT_FOLDER_ID]}"
    echo ""
    echo -e "${CYAN}N8N API Key:${NC}  ${ENV_VALS[N8N_API_KEY]:0:15}..."
    echo ""
}

# =============================================
# INÍCIO DO SCRIPT
# =============================================

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}     Instalador: Agente Smith (VPS & n8n)     ${NC}"
echo -e "${BLUE}==============================================${NC}\n"

# Flag --reconfig: pula direto pra reconfiguração
RECONFIG=false
if [ "$1" == "--reconfig" ]; then
    RECONFIG=true
    echo -e "${YELLOW}Modo de reconfiguração ativado.${NC}\n"
    load_existing_env
fi

# ─────────────────────────────────
# ETAPA 1: Checagem de dependências
# ─────────────────────────────────
echo -e "${YELLOW}[1/5] Verificando dependências do sistema...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Erro: Docker não está instalado.${NC}"
    echo "  curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo -e "${RED}Erro: Docker Compose não está instalado.${NC}"
    echo "  sudo apt-get update && sudo apt-get install docker-compose-plugin"
    exit 1
fi

echo -e "${GREEN}✔ Docker e Docker Compose encontrados.${NC}\n"

# ─────────────────────────────────
# ETAPA 2: Auto-Discovery de portas
# ─────────────────────────────────
MODE="FULL"

if [ "$RECONFIG" == "false" ]; then
    PORT_N8N_USED=false
    PORT_PG_USED=false

    (echo > /dev/tcp/127.0.0.1/5678) >/dev/null 2>&1 && PORT_N8N_USED=true
    (echo > /dev/tcp/127.0.0.1/5432) >/dev/null 2>&1 && PORT_PG_USED=true

    if [ "$PORT_N8N_USED" == "true" ] || [ "$PORT_PG_USED" == "true" ]; then
        echo -e "${YELLOW}⚠  Serviços detectados neste servidor:${NC}"
        [ "$PORT_N8N_USED" == "true" ] && echo -e "   • Porta 5678 (n8n) ${GREEN}em uso${NC}"
        [ "$PORT_PG_USED" == "true" ]  && echo -e "   • Porta 5432 (PostgreSQL) ${GREEN}em uso${NC}"
        echo ""
        read -p "Deseja instalar APENAS a API do Smith e usar seu N8N/Postgres existente? (s/n): " RESP
        if [[ "$RESP" =~ ^[sS]$ ]]; then
            MODE="API_ONLY"
            echo -e "${GREEN}✔ Modo API_ONLY: apenas o container smith-api será instalado.${NC}\n"
        else
            echo -e "${RED}Instalação cancelada. Libere as portas ou escolha 's'.${NC}"
            exit 1
        fi
    fi
fi

# ─────────────────────────────────
# ETAPA 3: Coleta de credenciais
# ─────────────────────────────────
collect_credentials() {
    echo -e "${YELLOW}[2/5] Configuração das Variáveis de Ambiente${NC}"
    echo -e "${CYAN}Preencha as credenciais abaixo. Campos obrigatórios marcados com *.${NC}\n"

    echo -e "${BOLD}── Anthropic ──${NC}"
    ask "ANTHROPIC_API_KEY" "* Chave da API (sk-ant-...)" "${ENV_VALS[ANTHROPIC_API_KEY]}" "true"

    echo -e "\n${BOLD}── WhatsApp (Z-API) ──${NC}"
    ask "ZAPI_INSTANCE_ID"  "* Instance ID"               "${ENV_VALS[ZAPI_INSTANCE_ID]}"  "true"
    ask "ZAPI_TOKEN"        "* Token da instância"         "${ENV_VALS[ZAPI_TOKEN]}"        "true"
    ask "ZAPI_CLIENT_TOKEN" "* Client Token"               "${ENV_VALS[ZAPI_CLIENT_TOKEN]}" "true"
    ask "CEO_WHATSAPP"      "* WhatsApp do CEO (5541...)"  "${ENV_VALS[CEO_WHATSAPP]}"      "true"

    echo -e "\n${BOLD}── PostgreSQL ──${NC}"
    if [ "$MODE" == "FULL" ]; then
        ENV_VALS[POSTGRES_HOST]="postgres"
        ask "POSTGRES_PASSWORD" "* Senha forte (será criada)" "${ENV_VALS[POSTGRES_PASSWORD]}" "true"
        ENV_VALS[POSTGRES_PORT]="5432"
        ENV_VALS[POSTGRES_DB]="smith_project"
        ENV_VALS[POSTGRES_USER]="postgres"
    else
        echo -e "  ${CYAN}Informe os dados do seu PostgreSQL existente:${NC}"
        ask "POSTGRES_HOST"     "* IP/Host do PostgreSQL"  "${ENV_VALS[POSTGRES_HOST]}"                "true"
        ask "POSTGRES_PORT"     "  Porta"                  "${ENV_VALS[POSTGRES_PORT]:-5432}"           "false"
        ask "POSTGRES_USER"     "  Usuário"                "${ENV_VALS[POSTGRES_USER]:-postgres}"       "false"
        ask "POSTGRES_DB"       "  Nome do banco"          "${ENV_VALS[POSTGRES_DB]:-smith_project}"    "false"
        ask "POSTGRES_PASSWORD" "* Senha do PostgreSQL"    "${ENV_VALS[POSTGRES_PASSWORD]}"             "true"
    fi

    echo -e "\n${BOLD}── Google Drive (OAuth2) ──${NC}"
    echo -e "  ${CYAN}Crie em: console.cloud.google.com → Credenciais → ID do cliente OAuth → App Desktop${NC}"
    ask "GOOGLE_CLIENT_ID"     "  Client ID (.apps.googleusercontent.com)"  "${ENV_VALS[GOOGLE_CLIENT_ID]}"     "false"
    ask "GOOGLE_CLIENT_SECRET" "  Client Secret (GOCSPX-...)"              "${ENV_VALS[GOOGLE_CLIENT_SECRET]}" "false"
    ask "GDRIVE_ROOT_FOLDER_ID" "  ID da pasta raiz no Drive"              "${ENV_VALS[GDRIVE_ROOT_FOLDER_ID]}" "false"

    echo -e "\n${BOLD}── N8N ──${NC}"
    echo -e "  ${CYAN}Informe a URL do seu n8n (ex: https://n8n.seudominio.com ou http://IP:5678)${NC}"
    ask "N8N_BASE_URL"         "* URL do painel n8n"                                  "${ENV_VALS[N8N_BASE_URL]}"         "true"
    ask "N8N_WEBHOOK_BASE_URL" "  URL base de webhooks (geralmente a mesma + /webhook)" "${ENV_VALS[N8N_WEBHOOK_BASE_URL]:-${ENV_VALS[N8N_BASE_URL]}/webhook}" "false"
    ask "N8N_API_KEY"          "  API Key do n8n (Settings → API)"                    "${ENV_VALS[N8N_API_KEY]}"          "false"
}

# Coleta + Revisão (loop até o usuário confirmar)
while true; do
    collect_credentials

    show_summary

    read -p "As informações estão corretas? (s = salvar / n = corrigir / q = sair): " CONFIRM
    case "$CONFIRM" in
        s|S)
            write_env
            break
            ;;
        n|N)
            echo -e "\n${YELLOW}Vamos refazer as perguntas. Os valores anteriores aparecerão como padrão.${NC}\n"
            continue
            ;;
        q|Q)
            echo -e "${RED}Instalação cancelada.${NC}"
            exit 0
            ;;
        *)
            echo -e "${YELLOW}Opção inválida. Digite 's' para salvar, 'n' para corrigir ou 'q' para sair.${NC}"
            ;;
    esac
done

# Se era apenas reconfiguração, para aqui
if [ "$RECONFIG" == "true" ]; then
    echo -e "\n${GREEN}Reconfiguração concluída! Para aplicar, reinicie os containers:${NC}"
    echo -e "  docker compose restart smith-api"
    exit 0
fi

# ─────────────────────────────────
# ETAPA 4: Subindo contêineres
# ─────────────────────────────────
echo -e "\n${YELLOW}[3/5] Inicializando infraestrutura Docker...${NC}"

COMPOSE_CMD="docker-compose"
if docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
fi

if [ "$MODE" == "FULL" ]; then
    $COMPOSE_CMD --profile full up -d --build
else
    $COMPOSE_CMD up -d --build smith-api
fi

echo -e "${GREEN}✔ Contêineres carregados.${NC}"
echo "Aguardando 10 segundos para a API estabilizar..."
sleep 10

echo -e "Executando setup do banco de dados..."
curl -s -X POST http://localhost:8000/setup > /dev/null \
    && echo -e "${GREEN}✔ Setup do banco concluído.${NC}" \
    || echo -e "${YELLOW}⚠ Setup do banco falhou. Rode manualmente: curl -X POST http://localhost:8000/setup${NC}"

# ─────────────────────────────────
# ETAPA 4.5: Auth Google Drive
# ─────────────────────────────────
if [ -n "${ENV_VALS[GOOGLE_CLIENT_ID]}" ]; then
    echo -e "\n${YELLOW}[4/5] Autenticação Google Drive (OAuth2)...${NC}"
    echo -e "Uma URL será exibida. Copie, abra no seu navegador, faça login e cole o código aqui."
    docker exec -it smith_api python tools/gdrive_auth.py
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✔ Google Drive autenticado.${NC}"
    else
        echo -e "${YELLOW}⚠ Pule por agora. Rode depois: docker exec -it smith_api python tools/gdrive_auth.py${NC}"
    fi
else
    echo -e "\n${YELLOW}[4/5] Google Drive: GOOGLE_CLIENT_ID não informado, pulando.${NC}"
fi

# ─────────────────────────────────
# ETAPA 5: Importação de workflows
# ─────────────────────────────────
echo -e "\n${YELLOW}[5/5] Importação dos Workflows no N8N...${NC}"

N8N_API="${ENV_VALS[N8N_API_KEY]}"
N8N_URL="${ENV_VALS[N8N_BASE_URL]}"

# Remove trailing slash da URL
N8N_URL="${N8N_URL%/}"

if [ -z "$N8N_API" ] || [ -z "$N8N_URL" ]; then
    echo -e "${YELLOW}⚠ N8N_API_KEY ou N8N_BASE_URL não configurados. Importe os .json da pasta workflows/ manualmente pelo painel do n8n.${NC}"
else
    # Testa conexão com n8n antes de importar
    echo -n "  Testando conexão com n8n ($N8N_URL)..."
    TEST_STATUS=$(curl -s -w "%{http_code}" -o /dev/null --max-time 10 "$N8N_URL/api/v1/workflows?limit=1" \
         -H "X-N8N-API-KEY: $N8N_API")
    if [ "$TEST_STATUS" != "200" ]; then
        echo -e " ${RED}✗ (HTTP $TEST_STATUS)${NC}"
        echo -e "${YELLOW}⚠ Não foi possível conectar ao n8n. Verifique a URL e API Key. Importe manualmente.${NC}"
    else
        echo -e " ${GREEN}✔ Conectado${NC}"
        if [ -d "workflows" ]; then
            mkdir -p .tmp_workflows
            cp workflows/*.json .tmp_workflows/

            # Detecta IP (para substituição nos workflows)
            HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
            [ -z "$HOST_IP" ] && HOST_IP="127.0.0.1"

            if [ "$MODE" == "API_ONLY" ]; then
                echo "  Ajustando rotas nos workflows (smith-api:8000 → $HOST_IP:8000)..."
                find .tmp_workflows/ -type f -name "*.json" -exec sed -i "s|smith-api:8000|$HOST_IP:8000|g" {} +
                find .tmp_workflows/ -type f -name "*.json" -exec sed -i "s|localhost:8000|$HOST_IP:8000|g" {} +
            fi

            for f in .tmp_workflows/*.json; do
                [ -f "$f" ] || continue
                FNAME=$(basename "$f")
                echo -n "  Enviando $FNAME..."
                STATUS=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$N8N_URL/api/v1/workflows" \
                     -H "X-N8N-API-KEY: $N8N_API" \
                     -H "Content-Type: application/json" \
                     -d @"$f")
                if [ "$STATUS" == "200" ] || [ "$STATUS" == "201" ]; then
                    echo -e " ${GREEN}✔${NC}"
                else
                    echo -e " ${RED}✗ (HTTP $STATUS)${NC}"
                fi
            done
            rm -rf .tmp_workflows
        else
            echo -e "${RED}Pasta workflows/ não encontrada.${NC}"
        fi
    fi
fi

# ─────────────────────────────────
# CONCLUSÃO
# ─────────────────────────────────
echo ""
echo -e "${BLUE}==============================================${NC}"
echo -e "${GREEN}  ✅ Deploy do Agente Smith concluído!${NC}"
echo -e "${BLUE}==============================================${NC}"
echo ""
if [ "$MODE" == "FULL" ]; then
    echo -e "  N8N:       http://<IP-DA-VPS>:5678"
fi
echo -e "  Smith API: http://<IP-DA-VPS>:8000"
echo -e "  Swagger:   http://<IP-DA-VPS>:8000/docs"
echo ""
echo -e "${CYAN}Dica: Para corrigir credenciais depois, rode:${NC}"
echo -e "  ${BOLD}./deploy.sh --reconfig${NC}"
echo ""
