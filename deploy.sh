#!/bin/bash

# Cores para o terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}     Instalador: Agente Smith (VPS & n8n)     ${NC}"
echo -e "${BLUE}==============================================${NC}\n"

# 1. Checagem de dependências
echo -e "${YELLOW}[1/4] Verificando dependências do sistema...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Erro: Docker não está instalado.${NC}"
    echo "Para instalar no Ubuntu, rode:"
    echo "  curl -fsSL https://get.docker.com -o get-docker.sh"
    echo "  sudo sh get-docker.sh"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Erro: Docker Compose não está instalado.${NC}"
    echo "Para instalar no Ubuntu, rode:"
    echo "  sudo apt-get update && sudo apt-get install docker-compose-plugin"
    exit 1
fi

echo -e "${GREEN}✔ Docker e Docker Compose encontrados.${NC}\n"

# Auto-Discovery - Verificando portas
# Retorna 0 se a porta estiver em uso, algo diferente caso contrário
PORT_5678_USED=0
PORT_5432_USED=0

(echo > /dev/tcp/127.0.0.1/5678) >/dev/null 2>&1 || PORT_5678_USED=1
(echo > /dev/tcp/127.0.0.1/5432) >/dev/null 2>&1 || PORT_5432_USED=1

MODE="FULL"

if [ $PORT_5678_USED -eq 0 ] || [ $PORT_5432_USED -eq 0 ]; then
    echo -e "${YELLOW}⚠️ Aviso: Detectamos que a porta 5678 (n8n) ou 5432 (Postgres) já está em uso no seu servidor.${NC}"
    echo -e "Você provavelmente já tem o N8N e/ou Postgres rodando (ex: via Portainer)."
    echo ""
    read -p "Você deseja instalar APENAS a API do Smith e conectar ao seu N8N/Postgres Existentes? (s/n): " RESP_MODE
    if [[ "$RESP_MODE" == "s" || "$RESP_MODE" == "S" ]]; then
        MODE="API_ONLY"
        echo -e "${GREEN}✔ Modo Plug-and-Play ativado: O script instalará apenas o container smith-api e fará a ponte.${NC}\n"
    else
        echo -e "${RED}Instalação interrompida. Libere as portas para continuar a instalação completa (full).${NC}"
        exit 1
    fi
fi

# Detecta IP primário da máquina para substituir nos webhooks se API_ONLY
HOST_IP=$(hostname -I | awk '{print $1}')
if [ -z "$HOST_IP" ]; then
    HOST_IP="127.0.0.1" # fallback
fi

# 2. Configuração do arquivo .env
echo -e "${YELLOW}[2/4] Configuração das Variáveis de Ambiente...${NC}"

if [ ! -f .env ]; then
    echo -e "O arquivo .env não foi encontrado. Copiando de .env.example...\n"
    cp .env.example .env
fi

# Função auxiliar para perguntar e substituir no .env
ask_and_set() {
    local KEY=$1
    local DISPLAY_NAME=$2
    local DEFAULT_VAL=$3
    local CURRENT_VAL=$(grep "^$KEY=" .env | cut -d '=' -f2)
    
    if [ -z "$CURRENT_VAL" ] || [ "$CURRENT_VAL" == '""' ]; then
        if [ -n "$DEFAULT_VAL" ]; then
            read -p "$DISPLAY_NAME ($KEY) [Pressione Enter para usar o padrão: $DEFAULT_VAL]: " USER_INPUT
            if [ -z "$USER_INPUT" ]; then
                USER_INPUT="$DEFAULT_VAL"
            fi
        else
            read -p "$DISPLAY_NAME ($KEY): " USER_INPUT
        fi
        
        if [ -n "$USER_INPUT" ]; then
            ESCAPED_INPUT=$(printf '%s\n' "$USER_INPUT" | sed -e 's/[\/&]/\\&/g')
            sed -i "s|^$KEY=.*|$KEY=$ESCAPED_INPUT|g" .env
        fi
    fi
}

ask_and_set "ANTHROPIC_API_KEY" "Chave da API da Anthropic (sk-ant-...)" ""
ask_and_set "ZAPI_INSTANCE_ID" "Z-API Instance ID" ""
ask_and_set "ZAPI_TOKEN" "Z-API Token" ""
ask_and_set "ZAPI_CLIENT_TOKEN" "Z-API Client Token" ""
ask_and_set "CEO_WHATSAPP" "Número de WhatsApp do CEO (Ex: 5541999999999)" ""

# Se Modo for FULL, o banco sobe no docker local com nome 'postgres'
# Se for API_ONLY, nós precisamos perguntar onde tá o Postgres nativo do cliente
if [ "$MODE" == "FULL" ]; then
    ask_and_set "POSTGRES_HOST" "Host do PostgreSQL" "postgres"
    ask_and_set "POSTGRES_PASSWORD" "Senha forte para o banco (PostgreSQL local)" ""
else
    echo -e "\n${BLUE}--- Credenciais do seu Postgres Existente ---${NC}"
    # Pergunta abertamente para o cara
    ask_and_set "POSTGRES_HOST" "Host/IP do PostgreSQL" "$HOST_IP"
    ask_and_set "POSTGRES_PORT" "Porta do PostgreSQL" "5432"
    ask_and_set "POSTGRES_USER" "Usuário do Postgres" "postgres"
    ask_and_set "POSTGRES_DB" "Nome do Banco que vamos criar" "smith_project"
    ask_and_set "POSTGRES_PASSWORD" "Senha do seu Postgres" ""
fi

echo -e "\n${BLUE}--- Credenciais Google Drive (OAuth2) ---${NC}"
ask_and_set "GOOGLE_CLIENT_ID" "Google Client ID (ex: 123456-abc.apps.googleusercontent.com)" ""
ask_and_set "GOOGLE_CLIENT_SECRET" "Google Client Secret (ex: GOCSPX-xxx)" ""
ask_and_set "GDRIVE_ROOT_FOLDER_ID" "ID da Pasta Inicial do Google Drive" ""
ask_and_set "N8N_API_KEY" "N8N API Key (necessária para importar workflows)" ""

echo -e "${GREEN}✔ Arquivo .env configurado com credenciais providas.${NC}\n"

# 3. Subindo os Contêineres
echo -e "${YELLOW}[3/4] Inicializando infraestrutura Docker...${NC}"

COMPOSE_PREFIX="docker-compose"
if docker compose version &> /dev/null; then
    COMPOSE_PREFIX="docker compose"
fi

if [ "$MODE" == "FULL" ]; then
    # Inicia a API + os profiles default full (Postgres e N8N)
    $COMPOSE_PREFIX --profile full up -d --build
else
    # Inicia SÓ a API
    $COMPOSE_PREFIX up -d --build smith-api
fi

echo -e "${GREEN}✔ Contêineres carregados.${NC}\n"
echo "Aguardando 10 segundos para a API estabilizar na porta 8000..."
sleep 10
echo -e "Criação das tabelas do projeto correndo na base..."
curl -s -X POST http://localhost:8000/setup > /dev/null && echo -e " ${GREEN}✔ Setup inicial SQL concluído.${NC}" || echo -e "${RED}Aviso: Falha ao acionar webhook de setup na API.${NC}"

# 3.5 Autenticação Google Drive (OAuth2)
GOOGLE_CID=$(grep "^GOOGLE_CLIENT_ID=" .env | cut -d '=' -f2)
if [ -n "$GOOGLE_CID" ] && [ "$GOOGLE_CID" != '""' ]; then
    echo -e "\n${YELLOW}[3.5/5] Autenticação Google Drive (OAuth2)...${NC}"
    echo -e "Uma URL será exibida. Copie, abra no navegador, faça login e cole o código aqui."
    docker exec -it smith-api python tools/gdrive_auth.py
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✔ Google Drive autenticado com sucesso.${NC}\n"
    else
        echo -e "${YELLOW}⚠ Autenticação Google Drive ignorada. Rode depois: docker exec -it smith-api python tools/gdrive_auth.py${NC}\n"
    fi
else
    echo -e "\n${YELLOW}⚠ GOOGLE_CLIENT_ID não configurado, pulando autenticação Drive.${NC}\n"
fi

# 4. Importação de Workflows no n8n
echo -e "${YELLOW}[4/5] Injeção Automática dos Workflows no N8N...${NC}"
N8N_API=$(grep "^N8N_API_KEY=" .env | cut -d '=' -f2)

if [ -z "$N8N_API" ] || [ "$N8N_API" == '""' ]; then
    echo -e "${RED}Aviso: N8N_API_KEY não localizada. Importe os arquivos da pasta 'workflows/' manualmente via Painel.${NC}"
else
    echo "Importando workflows automaticamente para o n8n..."
    if [ -d "workflows" ]; then
        # Copia workflows para uma pasta temporária para não mutacionar os originais do git localmente
        mkdir -p .tmp_workflows
        cp workflows/*.json .tmp_workflows/
        
        # Se mode API_ONLY, corrige as referências 'smith-api:8000' para o IP da VPS onde a API foi exposta na 8000
        if [ "$MODE" == "API_ONLY" ]; then
            echo "Substituindo rotas (smith-api:8000 -> $HOST_IP:8000) nos workflows para conexão plug-and-play..."
            find .tmp_workflows/ -type f -name "*.json" -exec sed -i "s|smith-api:8000|$HOST_IP:8000|g" {} +
            find .tmp_workflows/ -type f -name "*.json" -exec sed -i "s|localhost:8000|$HOST_IP:8000|g" {} +
        fi
        
        for f in .tmp_workflows/*.json; do
            if [ -f "$f" ]; then
                echo -n "Enviando $f..."
                # Assumimos que o n8n do usuário roda na porta 5678, mesmo se for mode API_ONLY
                # Trocamos para apontar para localhost:5678 (já que o N8n deve estar acessível na máquina rodando esse script)
                STATUS=$(curl -s -w "%{http_code}" -o /dev/null -X POST "http://localhost:5678/api/v1/workflows" \
                     -H "X-N8N-API-KEY: $N8N_API" \
                     -H "Content-Type: application/json" \
                     -d @"$f")
                if [ "$STATUS" == "200" ] || [ "$STATUS" == "201" ]; then
                    echo -e " ${GREEN}✔ OK${NC}"
                else
                    echo -e " ${RED}Falha (HTTP $STATUS)${NC}"
                fi
            fi
        done
        rm -rf .tmp_workflows
        echo -e "${GREEN}✔ Fim da importação dos workflows.${NC}"
    else
         echo -e "${RED}Pasta workflows/ não encontrada.${NC}"
    fi
fi

echo -e "\n${BLUE}==============================================${NC}"
echo -e "${GREEN}Deploy Dinâmico Concluído!${NC}"
if [ "$MODE" == "FULL" ]; then
    echo -e "O n8n da infra Smith está rodando em: http://$HOST_IP:5678"
else
    echo -e "A API do Smith está ativa em: http://$HOST_IP:8000 para acesso via seu N8n legado."
fi
echo -e "${BLUE}==============================================${NC}\n"
