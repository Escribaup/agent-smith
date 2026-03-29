import os
import json
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import Json
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

# Singleton logic for connection pool
_pool = None

def init_pool():
    global _pool
    if _pool is None:
        try:
            _pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                host=os.getenv("POSTGRES_HOST"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                database=os.getenv("POSTGRES_DB", "smith_project"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD")
            )
        except Exception as e:
            print(f"Erro ao conectar ao PostgreSQL: {e}")
            raise e

@contextmanager
def get_connection():
    if _pool is None:
        init_pool()
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        _pool.putconn(conn)

def create_schema() -> None:
    """Cria todas as tabelas se não existirem (idempotente)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS project_context (
                    id SERIAL PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    value JSONB NOT NULL,
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS messages_log (
                    id SERIAL PRIMARY KEY,
                    direction TEXT NOT NULL,
                    from_to TEXT NOT NULL,
                    text TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    processed BOOLEAN DEFAULT FALSE
                );

                CREATE TABLE IF NOT EXISTS decisions_log (
                    id SERIAL PRIMARY KEY,
                    phase TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    made_by TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS interviews (
                    id SERIAL PRIMARY KEY,
                    person_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    questions JSONB NOT NULL,
                    completed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    type TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    gdrive_id TEXT,
                    approved BOOLEAN DEFAULT FALSE,
                    version INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS phase_status (
                    phase TEXT PRIMARY KEY,
                    started BOOLEAN DEFAULT FALSE,
                    approved BOOLEAN DEFAULT FALSE,
                    started_at TIMESTAMP,
                    approved_at TIMESTAMP,
                    notes TEXT
                );
            """)

# ── Context (chave-valor flexível) ──────────────────────────

def get_context_value(key: str, default=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM project_context WHERE key = %s", (key,))
            res = cur.fetchone()
            if res:
                return res[0]
            return default

def set_context_value(key: str, value) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO project_context (key, value, updated_at) 
                VALUES (%s, %s, NOW())
                ON CONFLICT (key) DO UPDATE 
                SET value = EXCLUDED.value, updated_at = NOW()
            """, (key, Json(value)))
    return True

def get_full_context() -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT key, value FROM project_context")
            rows = cur.fetchall()
            
    # Reconstruct nested dict from dotted keys (e.g., "fases.fase1.aprovada")
    result = {}
    for k, v in rows:
        parts = k.split('.')
        current = result
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = v
    return result

def already_asked(question_key: str) -> bool:
    val = get_context_value(question_key)
    return val is not None

# ── Mensagens ────────────────────────────────────────────────

def log_message(direction: str, from_to: str, text: str) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO messages_log (direction, from_to, text) 
                VALUES (%s, %s, %s) RETURNING id
            """, (direction, from_to, text))
            return cur.fetchone()[0]

def mark_message_processed(message_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE messages_log SET processed = TRUE WHERE id = %s", (message_id,))

def get_pending_messages() -> list:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, direction, from_to, text, timestamp FROM messages_log WHERE processed = FALSE AND direction = 'in' ORDER BY timestamp ASC")
            rows = cur.fetchall()
            return [{"id": r[0], "direction": r[1], "from_to": r[2], "text": r[3], "timestamp": r[4]} for r in rows]

# ── Decisões ─────────────────────────────────────────────────

def log_decision(phase: str, decision: str, made_by: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO decisions_log (phase, decision, made_by) 
                VALUES (%s, %s, %s)
            """, (phase, decision, made_by))

def get_decisions_log(phase: str = None) -> list:
    query = "SELECT id, phase, decision, made_by, timestamp FROM decisions_log"
    params = []
    if phase:
        query += " WHERE phase = %s"
        params.append(phase)
    query += " ORDER BY timestamp ASC"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            return [{"id": r[0], "phase": r[1], "decision": r[2], "made_by": r[3], "timestamp": r[4]} for r in rows]

# ── Entrevistas ──────────────────────────────────────────────

def save_interview_answer(person_name: str, phone: str, phase: str, question: str, answer: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, questions FROM interviews WHERE person_name = %s AND phase = %s", (person_name, phase))
            res = cur.fetchone()
            if res:
                inter_id, questions = res
                questions.append({"question": question, "answer": answer})
                cur.execute("UPDATE interviews SET questions = %s WHERE id = %s", (Json(questions), inter_id))
            else:
                cur.execute("""
                    INSERT INTO interviews (person_name, phone, phase, questions) 
                    VALUES (%s, %s, %s, %s)
                """, (person_name, phone, phase, Json([{"question": question, "answer": answer}])))

def mark_interview_complete(person_name: str, phase: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE interviews SET completed = TRUE WHERE person_name = %s AND phase = %s", (person_name, phase))

def get_interview(person_name: str, phase: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT person_name, phone, phase, questions, completed FROM interviews WHERE person_name = %s AND phase = %s", (person_name, phase))
            res = cur.fetchone()
            if res:
                return {"person_name": res[0], "phone": res[1], "phase": res[2], "questions": res[3], "completed": res[4]}
            return None

def get_all_interviews(phase: str) -> list:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT person_name, phone, phase, questions, completed FROM interviews WHERE phase = %s", (phase,))
            rows = cur.fetchall()
            return [{"person_name": r[0], "phone": r[1], "phase": r[2], "questions": r[3], "completed": r[4]} for r in rows]

# ── Documentos ───────────────────────────────────────────────

def save_document(doc_type: str, phase: str, title: str, content: str, gdrive_id: str = None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents (type, phase, title, content, gdrive_id) 
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (doc_type, phase, title, content, gdrive_id))
            return cur.fetchone()[0]

def approve_document(doc_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE documents SET approved = TRUE, updated_at = NOW() WHERE id = %s", (doc_id,))

def get_documents(phase: str, doc_type: str = None) -> list:
    query = "SELECT id, type, phase, title, content, gdrive_id, approved, version FROM documents WHERE phase = %s"
    params = [phase]
    if doc_type:
        query += " AND type = %s"
        params.append(doc_type)
        
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            return [{"id": r[0], "type": r[1], "phase": r[2], "title": r[3], "content": r[4], "gdrive_id": r[5], "approved": r[6], "version": r[7]} for r in rows]

def update_document(doc_id: int, content: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE documents 
                SET content = %s, version = version + 1, updated_at = NOW() 
                WHERE id = %s
            """, (content, doc_id))

# ── Fases ────────────────────────────────────────────────────

def get_phase_status(phase: str) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT phase, started, approved, started_at, approved_at, notes FROM phase_status WHERE phase = %s", (phase,))
            res = cur.fetchone()
            if res:
                return {"phase": res[0], "started": res[1], "approved": res[2], "started_at": res[3], "approved_at": res[4], "notes": res[5]}
            return {}

def start_phase(phase: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE phase_status SET started = TRUE, started_at = NOW() WHERE phase = %s", (phase,))

def approve_phase(phase: str, notes: str = None) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE phase_status SET approved = TRUE, approved_at = NOW(), notes = %s WHERE phase = %s", (notes, phase))

def get_current_phase() -> str:
    """Lógica: última fase com started=true e approved=false."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT phase FROM phase_status WHERE started = TRUE AND approved = FALSE ORDER BY started_at DESC LIMIT 1")
            res = cur.fetchone()
            if res:
                return res[0]
            
            # Check if everything is approved
            cur.execute("SELECT count(*) FROM phase_status WHERE approved = FALSE")
            if cur.fetchone()[0] == 0:
                return 'concluido'
            
            return 'onboarding'
