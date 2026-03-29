import os
import sys
import argparse

# Garante path imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from tools import db_client, gdrive_client, whatsapp_client

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

def validate_env() -> list:
    """Retorna lista de variáveis faltando. Lista vazia = OK."""
    missing = []
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            missing.append(var)
    return missing

def create_database_if_not_exists() -> bool:
    """CREATE DATABASE IF NOT EXISTS simplificado via psycopg2 no db padrão."""
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    
    dbname = os.getenv("POSTGRES_DB", "smith_project")
    
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD"),
            database="postgres" # conectando no banco genérico pra criar o alvo
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (dbname,))
        exists = cur.fetchone()
        
        if not exists:
            cur.execute(f"CREATE DATABASE {dbname}")
            print(f"[OK] Banco '{dbname}' criado no PostgreSQL.")
        else:
            print(f"[OK] Banco '{dbname}' já existia.")
            
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Falha ao criar/verificar database '{dbname}': {e}")
        return False

def initialize_phases() -> None:
    """Insere registros iniciais na tabela phase_status para todas as fases."""
    from tools.phase_manager import PHASE_ORDER
    with db_client.get_connection() as conn:
        with conn.cursor() as cur:
            for phase in PHASE_ORDER:
                cur.execute("""
                    INSERT INTO phase_status (phase) 
                    VALUES (%s) ON CONFLICT DO NOTHING
                """, (phase,))
    
    # Marca onboarding como iniciado se ainda não foi
    status = db_client.get_phase_status("onboarding")
    if not status.get("started"):
        db_client.start_phase("onboarding")

def test_whatsapp_connection() -> bool:
    """Testa envio z-api ao CEO"""
    ceo = os.getenv("CEO_WHATSAPP")
    if not ceo:
        print("[ERROR] CEO_WHATSAPP não configurado para testes.")
        return False
    return whatsapp_client.send_message(ceo, "✅ *Agente Smith ativado.*\nSetup do banco de dados e integrações concluído com sucesso. Aguarde o início do processo de onboarding.")

def print_setup_summary(results: dict) -> None:
    """Imprime tabela com status de cada etapa do setup."""
    print("\n" + "="*40)
    print("📈  RESUMO DO SETUP: AGENTE SMITH ")
    print("="*40)
    
    for step, status in results.items():
        icon = "✅ OK" if status else "❌ FALHOU"
        print(f"[{icon}] {step}")
        
    print("="*40)
    if all(results.values()):
        print("Tudo pronto! O Agent Smith está preparado para rodar no N8N.")
    else:
        print("Atenção: algumas etapas falharam. Verifique os logs e .env.")

if __name__ == "__main__":
    print("=== Inicializando Setup Agente Smith ===")
    results = {}
    
    # 1. Valida .env
    missing = validate_env()
    results["Variáveis .env"] = (len(missing) == 0)
    if missing:
        print(f"Faltam as variáveis: {missing}")
        
    # 2. Cria banco target (se for postgres sysadmin)
    results["Database Access"] = create_database_if_not_exists()
    
    # 3. Cria schema tables
    try:
        db_client.create_schema()
        results["Table Schemas"] = True
    except Exception as e:
        print(f"Erro ao criar tabelas: {e}")
        results["Table Schemas"] = False
        
    # 4. Inicializa fases
    try:
        initialize_phases()
        results["Registros de Fases"] = True
    except Exception as e:
        print(f"Erro init phases: {e}")
        results["Registros de Fases"] = False
        
    # 5. Setup Drive Folders
    try:
        folders = gdrive_client.setup_document_folders(os.getenv("GDRIVE_ROOT_FOLDER_ID"))
        results["Google Drive Folders"] = bool(folders)
        if folders:
            # Salvar IDs no contexto db
            db_client.set_context_value("config.gdrive_folders", folders)
    except Exception as e:
        print(f"Erro GDrive setup: {e}")
        results["Google Drive Folders"] = False
        
    # 6. Testa Z-API WhatsApp
    args = argparse.ArgumentParser()
    args.add_argument("--skip-whatsapp", action="store_true")
    parsed = args.parse_args()
    
    if not parsed.skip_whatsapp:
        results["WhatsApp Z-API Connection"] = test_whatsapp_connection()
    else:
        results["WhatsApp Z-API Connection (PULADO)"] = True

    # 7. Resumo final
    print_setup_summary(results)
