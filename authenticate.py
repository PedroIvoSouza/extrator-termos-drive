import os.path
import sys
import json  # Importamos a biblioteca JSON

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def main():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # --- MUDANÇA FINAL AQUI ---
            # Carregamos o arquivo de credenciais manualmente como um dicionário
            with open('credentials.json', 'r') as f:
                client_config = json.load(f)

            # Criamos o fluxo de autenticação a partir da configuração carregada
            # e passamos explicitamente a redirect_uri.
            # Isso força o uso do valor correto que está no arquivo.
            flow = InstalledAppFlow.from_client_config(
                client_config,
                SCOPES,
                redirect_uri=client_config['web']['redirect_uris'][0]
            )
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f"\nPor favor, acesse esta URL para autorizar o acesso:\n{auth_url}\n")
            
            sys.stdout.flush() 
            code = input("Cole o código de autorização do seu navegador aqui: ")
            
            flow.fetch_token(code=code)
            creds = flow.credentials
        
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("drive", "v3", credentials=creds)
        print("\nAutenticação com Google Drive bem-sucedida!")
        # ... (o resto do código de teste permanece o mesmo) ...
        
    except HttpError as error:
        print(f"Ocorreu um erro: {error}")

if __name__ == "__main__":
    main()