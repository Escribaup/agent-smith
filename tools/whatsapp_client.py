import os
import httpx
from dotenv import load_dotenv

load_dotenv()

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
ZAPI_BASE_URL = os.getenv("ZAPI_BASE_URL", "https://api.z-api.io/instances")
CEO_WHATSAPP = os.getenv("CEO_WHATSAPP")

def _get_zapi_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_CLIENT_TOKEN
    }

def send_message(to: str, text: str) -> bool:
    """
    Envia mensagem de texto via Z-API.
    Endpoint: POST {ZAPI_BASE_URL}/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text
    Máximo 4096 chars. Retorna True se status 200.
    """
    if not all([ZAPI_INSTANCE_ID, ZAPI_TOKEN, ZAPI_CLIENT_TOKEN]):
        print("Configurações da Z-API ausentes")
        return False
        
    url = f"{ZAPI_BASE_URL}/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
    payload = {
        "phone": to, # apenas números
        "message": text[:4096]
    }
    
    retries = [1, 2, 4]
    
    for wait_time in retries:
        try:
            response = httpx.post(url, headers=_get_zapi_headers(), json=payload, timeout=10)
            if response.status_code == 200:
                print(f"Mensagem enviada com sucesso para {to}")
                return True
            print(f"Erro na Z-API: {response.text}")
        except Exception as e:
            print(f"Exceção enviando mensagem via Z-API: {e}")
            
        import time
        time.sleep(wait_time)
        
    print(f"Falha ao enviar mensagem para {to} após todas as tentativas.")
    return False

def parse_incoming_webhook(payload: dict) -> dict | None:
    """Parseia payload do webhook Z-API."""
    try:
        from_me = payload.get("fromMe", False)
        type_str = payload.get("type", "")
        
        if from_me or type_str != "ReceivedCallback":
            return None
            
        text_obj = payload.get("text", {})
        message = text_obj.get("message", None)
        
        if not message:
            return None
            
        return {
            "from": payload.get("phone"),
            "text": message,
            "timestamp": payload.get("momment")
        }
    except Exception as e:
        print(f"Erro ao parsear payload webhook: {e}")
        return None

def is_from_ceo(sender: str) -> bool:
    """Verifica se remetente é o CEO."""
    if not CEO_WHATSAPP or not sender: return False
    
    clean_sender = sender.replace("@s.whatsapp.net", "").strip()
    return clean_sender == CEO_WHATSAPP.strip()

def format_message(lines: list) -> str:
    """
    Formata lista de linhas em mensagem WhatsApp.
    Máximo 5 linhas. Trunca se necessário com "..."
    """
    if len(lines) > 5:
        lines = lines[:4] + ["..."]
    
    # Sanitiza markdown
    clean_lines = []
    for line in lines:
        line = line.replace("*", "").replace("#", "").replace("_", "").replace("`", "")
        clean_lines.append(line)
        
    return "\n".join(clean_lines)
