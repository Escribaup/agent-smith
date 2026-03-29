"""
Script auxiliar para autenticação OAuth2 do Google Drive.
Rode este script uma única vez para gerar o token.json.

Uso:
    python tools/gdrive_auth.py

O script vai mostrar uma URL. Copie, cole no navegador do seu computador,
faça login na conta Google, copie o código de autorização e cole de volta
no terminal.
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_PATH = os.path.join(os.path.dirname(__file__), '..', 'token.json')


def main():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("❌ GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET devem estar no .env")
        print("   Crie as credenciais em: https://console.cloud.google.com/apis/credentials")
        print("   Tipo: ID do cliente OAuth → Aplicativo para computador")
        sys.exit(1)

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
        }
    }

    print("\n🔑 Autenticação Google Drive (OAuth2)")
    print("=" * 50)
    print("Uma URL será gerada. Copie e abra no navegador.")
    print("Faça login e cole o código de autorização aqui.\n")

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_console()

    with open(TOKEN_PATH, 'w') as f:
        f.write(creds.to_json())

    print(f"\n✅ Token salvo em: {os.path.abspath(TOKEN_PATH)}")
    print("O Agente Smith agora tem acesso ao Google Drive.")


if __name__ == "__main__":
    main()
