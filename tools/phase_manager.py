import datetime

try:
    from tools import db_client
    from tools import context_manager
except ImportError:
    import db_client
    import context_manager

PHASE_ORDER = ["onboarding", "fase1", "fase2", "fase3", "fase4", "fase5", "concluido"]

PHASE_LABELS = {
    "fase1": "Fase 1 — Diagnóstico",
    "fase2": "Fase 2 — Especialização",
    "fase3": "Fase 3 — Capital Fixo",
    "fase4": "Fase 4 — Incentivos",
    "fase5": "Fase 5 — Mercado"
}

def get_current_phase(context: dict = None) -> str:
    """Retorna fase atual do projeto via db_client."""
    return db_client.get_current_phase()

def can_advance(context: dict = None) -> bool:
    """Verifica se fase atual está aprovada e pode avançar."""
    return context_manager.can_advance()

def advance_phase(context: dict = None) -> dict:
    """
    Avança para próxima fase. Atualiza contexto.
    Nunca avança sem can_advance() == True.
    """
    if not can_advance():
        raise Exception("Não é possível avançar: a fase atual não foi aprovada pelo CEO.")
        
    current = get_current_phase()
    if current == 'concluido':
        return {"status": "Projeto já concluído", "fase": "concluido"}
        
    idx = PHASE_ORDER.index(current)
    next_phase = PHASE_ORDER[idx + 1]
    
    # Marca a próxima como iniciada
    db_client.start_phase(next_phase)
    
    return {"status": "Avançado com sucesso", "fase_anterior": current, "nova_fase": next_phase}

def get_phase_summary(context: dict = None, phase: str = None) -> str:
    """
    Retorna resumo formatado de uma fase para o relatório semanal.
    """
    if not phase:
        phase = get_current_phase()
        
    status = db_client.get_phase_status(phase)
    label = PHASE_LABELS.get(phase, phase.capitalize())
    
    iniciada = "Sim" if status.get("started") else "Não"
    aprovada = "Sim" if status.get("approved") else "Não"
    
    return f"[{label}] - Iniciada: {iniciada} | Aprovada: {aprovada}"

def is_blocked(context: dict = None, hours: int = 48) -> bool:
    """
    Verifica se há bloqueio ativo (mensagem pendente ou falta de decisão)
    há mais de `hours` horas.
    """
    import datetime
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)
    
    # Em um banco real, avaliaríamos decisions_log ou pending_messages com timestamp <= cutoff
    # Aqui, verificamos a última interação
    
    pending = db_client.get_pending_messages()
    if not pending:
        # Se não há pendência na fila in, então não tem bloqueio por resposta do CEO. 
        # (Lógica simplificada conforme escopo)
        return False
        
    oldest_pending = pending[0]
    if oldest_pending.get('timestamp') and oldest_pending['timestamp'] <= cutoff:
        return True
        
    return False
