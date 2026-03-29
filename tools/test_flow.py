import os
import sys
from dotenv import load_dotenv
from pprint import pprint

# Adiciona o diretório raiz do projeto ao path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from tools import context_manager, db_client

def simulate_chat():
    """Simula uma sessão de chat no terminal atualizando o contexto Postgres"""
    
    print("="*50)
    print("AGENTE SMITH - MODO SIMULAÇÃO LOCAL")
    print("="*50)
    
    try:
        db_client.create_schema()
        print("[+] Schema do banco de dados verificado.")
    except Exception as e:
        print(f"[-] Erro de BD. Verifique as variáveis no .env.\nDetalhe: {str(e)}")
        return

    print("\n[ Comando: 'sair' para encerrar a simulação ]")
    print("[ Comando: 'contexto' para visualizar o estado atual ]\n")

    user_phone = "SIMULADOR_TESTE"
    
    while True:
        try:
            msg = input(f"[{user_phone}] > ")
        except (KeyboardInterrupt, EOFError):
            break
            
        if msg.lower().strip() == 'sair':
            break
        elif msg.lower().strip() == 'contexto':
            ctx = context_manager.get_context()
            print("\n--- CONTEXTO ATUAL ---")
            pprint(ctx)
            print("----------------------\n")
            continue
            
        print("[Sistema] Registrando mensagem...")
        db_client.save_message(user_phone, msg, 'in', user_phone)
        db_client.log_decision('simulacao', f'Mensagem recebida: {msg}', 'system')
        
        # Em um cenário real, o n8n capturaria essa mensagem e enviaria pro LLM.
        # Aqui no teste local, apenas confirmamos as operações de BD.
        print("[Agente Smith Simulador] -> Mensagem gravada na base de dados com sucesso.")
        print("                            Para testar o LLM, o fluxo real do n8n deve ser acionado.\n")

if __name__ == "__main__":
    load_dotenv(os.path.join(project_root, '.env'))
    simulate_chat()
