from fastapi import FastAPI, HTTPException, Body
from typing import Any, Dict, Optional
import os

# Importa as ferramentas originais
# Nota: Esses módulos devem estar implementados na pasta tools/ conforme spec.md
try:
    from tools import context_manager, db_client, phase_manager, setup
except ImportError:
    # Fallback se a API subir antes dos arquivos serem escritos localmente (mock mode)
    pass

app = FastAPI(title="Agente Smith API", version="1.0", description="API wrapper para as ferramentas Python do Agente Smith")

@app.get("/")
def health_check():
    return {"status": "online", "message": "Agente Smith API rodando"}

@app.post("/setup")
def run_setup():
    """Roda a inicialização do banco de dados (setup.py)"""
    try:
        from tools import setup
        missing = setup.validate_env()
        if missing:
            raise HTTPException(status_code=400, detail=f"Faltam variáveis no .env: {missing}")
        
        setup.create_database_if_not_exists()
        from tools import db_client
        db_client.create_schema()
        setup.initialize_phases()
        
        return {"status": "success", "message": "Setup concluído com sucesso."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/context")
def get_full_context():
    """Retorna todo o contexto do projeto"""
    try:
        from tools import context_manager
        return context_manager.get_context()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/context")
def update_context(path: str = Body(..., embed=True), value: Any = Body(..., embed=True)):
    """Atualiza um valor específico no contexto (pontilhado)"""
    try:
        from tools import context_manager
        success = context_manager.set(path, value)
        return {"success": success, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/phase/current")
def get_current_phase():
    """Retorna a fase atual do projeto"""
    try:
        from tools import phase_manager
        return {"phase": phase_manager.get_current_phase(None)} # Adapte com base no db real
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
