import os
import json
import base64
from tempfile import NamedTemporaryFile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    """Inicializa cliente Drive via service account (base64 do .env)."""
    b64_creds = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not b64_creds:
        print("GOOGLE_SERVICE_ACCOUNT_JSON não configurado")
        return None
        
    try:
        creds_json = base64.b64decode(b64_creds).decode('utf-8')
        creds_dict = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Erro ao inicializar Google Drive API: {e}")
        return None

def create_folder(parent_id: str, name: str) -> str:
    """Cria pasta. Idempotente — retorna ID existente se já houver."""
    service = get_drive_service()
    if not service: return ""
    
    # Verifica se já existe
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    if files:
        return files[0]['id']
        
    # Cria nova pasta
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def write_document(parent_id: str, filename: str, content: str) -> str:
    """
    Cria ou atualiza arquivo .md no Drive. Retorna file_id.
    Se arquivo com mesmo nome existir no parent, faz update.
    """
    service = get_drive_service()
    if not service: return ""
    
    query = f"name='{filename}' and '{parent_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    # Cria arquivo local temporário
    with NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as tf:
        tf.write(content)
        temp_path = tf.name
        
    try:
        media = MediaFileUpload(temp_path, mimetype='text/markdown', resumable=True)
        if files:
            # Update existente
            file_id = files[0]['id']
            updated_file = service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
            return file_id
        else:
            # Novo arquivo
            file_metadata = {
                'name': filename,
                'parents': [parent_id]
            }
            new_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            return new_file.get('id')
    finally:
        os.remove(temp_path)

def get_shareable_link(file_id: str) -> str:
    """Torna arquivo público (view only) e retorna link."""
    service = get_drive_service()
    if not service: return ""
    
    try:
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        file_info = service.files().get(fileId=file_id, fields='webViewLink').execute()
        return file_info.get('webViewLink')
    except Exception as e:
        print(f"Erro ao tornar arquivo público: {e}")
        return ""

def setup_document_folders(root_folder_id: str) -> dict:
    """
    Cria pastas de documentos do projeto. Idempotente.
    Retorna: { "sops": folder_id, "relatorios": folder_id, "mapas": folder_id }
    """
    root_id = root_folder_id or os.getenv("GDRIVE_ROOT_FOLDER_ID")
    if not root_id:
        return {}
        
    smith_root = create_folder(root_id, "Agente Smith")
    
    sops_id = create_folder(smith_root, "SOPs")
    mapas_id = create_folder(smith_root, "Mapas de Processo")
    relatorios_id = create_folder(smith_root, "Relatórios de Diagnóstico")
    
    return {
        "smith_root": smith_root,
        "sops": sops_id,
        "mapas": mapas_id,
        "relatorios": relatorios_id
    }
