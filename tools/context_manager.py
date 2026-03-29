import os
import sys

# Garante import do db_client se tools estiver no PYTHON_PATH
try:
    from tools import db_client
except ImportError:
    import db_client

def get_context() -> dict:
    """
    Retorna contexto completo do projeto como dict.
    """
    ctx = db_client.get_full_context()
    return ctx if ctx else {}

def get(path: str, default=None):
    """
    Lê campo por path pontilhado. Ex: 'fases.fase1.aprovada'
    """
    return db_client.get_context_value(path, default)

def set(path: str, value) -> bool:
    """
    Define campo por path pontilhado. Ex: 'empresa.headcount'
    """
    return db_client.set_context_value(path, value)

def already_asked(question_key: str) -> bool:
    """
    Verifica se pergunta já foi feita (existe a chave no contexto).
    """
    return db_client.already_asked(question_key)

def get_current_phase() -> str:
    """
    Retorna fase atual do banco.
    """
    return db_client.get_current_phase()

def can_advance() -> bool:
    """
    Verifica se fase atual está aprovada para avançar.
    Lê phase_status da fase atual no banco.
    """
    current = get_current_phase()
    if current == 'concluido':
        return False
        
    status = db_client.get_phase_status(current)
    return status.get("approved", False)
