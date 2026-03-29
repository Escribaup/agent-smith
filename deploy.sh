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

# 2. Configuração do arquivo .env
echo -e "${YELLOW}[2/4] Configuração das Variáveis de Ambiente...${NC}"

if [ ! -f .env ]; then
    echo -e "O arquivo .env não foi encontrado. Vamos configurá-lo agora.\n"
    cp .env.example .env

    # Função auxiliar para perguntar e substituir no .env
    ask_and_set() {
        local KEY=$1
        local DISPLAY_NAME=$2
        local CURRENT_VAL=$(grep "^$KEY=" .env | cut -d '=' -f2)
        
        # Só pergunta se estiver vazio
        if [ -z "$CURRENT_VAL" ] || [ "$CURRENT_VAL" == '""' ]; then
            read -p "$DISPLAY_NAME ($KEY): " USER_INPUT
            # Substitui a linha no arquivo .env
            if [ -n "$USER_INPUT" ]; then
                # Escapa caracteres especiais para o sed
                ESCAPED_INPUT=$(printf '%s\n' "$USER_INPUT" | sed -e 's/[\/&]/\\&/g')
                sed -i "s|^$KEY=.*|$KEY=$ESCAPED_INPUT|g" .env
            fi
        fi
    }

    ask_and_set "ANTHROPIC_API_KEY" "Chave da API da Anthropic (sk-ant-...)"
    ask_and_set "ZAPI_INSTANCE_ID" "Z-API Instance ID"
    ask_and_set "ZAPI_TOKEN" "Z-API Token"
    ask_and_set "ZAPI_CLIENT_TOKEN" "Z-API Client Token"
    ask_and_set "CEO_WHATSAPP" "Número de WhatsApp do CEO (Ex: 5541999999999)"
    ask_and_set "POSTGRES_PASSWORD" "Crie uma senha forte para o banco de dados (PostgreSQL)"
    ask_and_set "GDRIVE_ROOT_FOLDER_ID" "ID da Pasta do Google Drive"
    ask_and_set "N8N_API_KEY" "N8N API Key (Pode ser gerada depois no painel n8n e inserida no .env)"
    
    # Opcional: Para o base64 do Google Auth, talvez seja longo pra colar no shell local:
    read -p "Cole o JSON (Base64) da Google Service Account (ou deixe vazio para adicionar manualmente depois): " G_JSON
    if [ -n "$G_JSON" ]; then
        sed -i "s|^GOOGLE_SERVICE_ACCOUNT_JSON=.*|GOOGLE_SERVICE_ACCOUNT_JSON=$G_JSON|g" .env
    fi

    echo -e "${GREEN}✔ Arquivo .env configurado.${NC}\n"
else
    echo -e "${GREEN}✔ Arquivo .env já existe. Utilizando configurações atuais.${NC}\n"
fi

# 3. Subindo os Contêineres
echo -e "${YELLOW}[3/4] Inicializando infraestrutura Docker...${NC}"

# Tenta usar o novo docker compose ou o antigo docker-compose
if docker compose version &> /dev/null; then
    docker compose up -d --build
else
    docker-compose up -d --build
fi

echo -e "${GREEN}✔ Contêineres em execução (n8n, postgres, smith-api).${NC}\n"

# Aguarda serviço da API ficar de pé para rodar o setup do banco
echo "Aguardando 10 segundos para os serviços inicializarem..."
sleep 10
echo -e "A inicialização das tabelas ocorrerá automaticamente pela API via porta 8000."
curl -X POST http://localhost:8000/setup || echo -e "${RED}Nota: O servidor FastAPI ainda não está 100% pronto. Rode tools/setup.py manualmente se der erro.${NC}"

# 4. Importação de Workflows no n8n
echo -e "\n${YELLOW}[4/4] Importação dos Workflows do n8n...${NC}"
# Verificando a API Key
N8N_API=$(grep "^N8N_API_KEY=" .env | cut -d '=' -f2)

if [ -z "$N8N_API" ] || [ "$N8N_API" == '""' ]; then
    echo -e "${RED}Atenção: N8N_API_KEY não localizada. Você precisará gerar uma API Key no painel do N8N e colocá-la no arquivo .env para importar os arquivos automaticamente.${NC}"
    echo -e "Como importar manualmente:"
    echo "1. Acesse o n8n no seu navegado (http://<seu-ip>:5678)"
    echo "2. Vá em 'Workflows' > 'Import from File' e selecione os JSONs da pasta 'workflows/'."
else
    echo "Importando workflows automaticamente para o n8n local..."
    if [ -d "workflows" ]; then
        for f in workflows/*.json; do
            if [ -f "$f" ]; then
                echo "Importando $f..."
                curl -s -X POST "http://localhost:5678/api/v1/workflows" \
                     -H "X-N8N-API-KEY: $N8N_API" \
                     -H "Content-Type: application/json" \
                     -d @"$f" > /dev/null
                echo -e " ${GREEN}✔ OK${NC}"
            fi
        done
        echo -e "${GREEN}✔ Workflows importados.${NC}"
    else
         echo -e "${RED}Pasta workflows/ não encontrada.${NC}"
    fi
fi

echo -e "\n${BLUE}==============================================${NC}"
echo -e "${GREEN}Deploy Concluído com Sucesso!${NC}"
echo -e "O n8n está rodando em: http://<IP-DA-SUA-VPS>:5678"
echo -e "O smith-api (FastAPI) está em: http://localhost:8000"
echo -e "${BLUE}==============================================${NC}\n"
