import os
import json
from tempfile import NamedTemporaryFile
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_PATH = os.path.join(os.path.dirname(__file__), '..', 'token.json')


def _build_client_config() -> dict:
    """Monta o dict de credenciais OAuth a partir das variáveis de ambiente."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        return {}
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
        }
    }


def get_drive_service():
    """Inicializa cliente Drive via OAuth2 (Client ID + token.json)."""
    creds = None

    # 1. Tenta carregar token salvo
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception:
            creds = None

    # 2. Refresh se expirou
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
        except Exception:
            creds = None

    # 3. Se ainda sem credencial, pede login interativo
    if not creds or not creds.valid:
        client_config = _build_client_config()
        if not client_config:
            print("[GDrive] GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET não configurados no .env")
            return None
        try:
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_console()
            with open(TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
            print("[GDrive] Token salvo com sucesso em token.json")
        except Exception as e:
            print(f"[GDrive] Erro durante autenticação OAuth: {e}")
            return None

    return build('drive', 'v3', credentials=creds)


def create_folder(parent_id: str, name: str) -> str:
    """Cria pasta. Idempotente — retorna ID existente se já houver."""
    service = get_drive_service()
    if not service:
        return ""

    query = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents and trashed=false"
    )
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    if files:
        return files[0]['id']

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
    if not service:
        return ""

    query = f"name='{filename}' and '{parent_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    with NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as tf:
        tf.write(content)
        temp_path = tf.name

    try:
        media = MediaFileUpload(temp_path, mimetype='text/markdown', resumable=True)
        if files:
            file_id = files[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
            return file_id
        else:
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
    if not service:
        return ""

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


def setup_document_folders(root_folder_id: str = None) -> dict:
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
