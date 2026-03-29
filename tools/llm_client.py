import os
import json
import traceback
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

def get_client() -> Anthropic:
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY não encontrada no .env")
    return Anthropic(api_key=ANTHROPIC_API_KEY)

def call_claude(
    system_prompt: str,
    user_message: str,
    model: str = "claude-3-5-haiku-20241022",
    max_tokens: int = 2048,
    temperature: float = 0.3,
    expect_json: bool = False
) -> str | dict:
    """
    Integração base com Claude. Usando cloude-3-5-haiku para velocidade.
    Faz validação e retry em caso de JSON inválido se expect_json for True.
    """
    client = get_client()
    
    def do_call(prompt_text: str):
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt_text}
            ]
        )
        return response.content[0].text
        
    initial_response = do_call(user_message)
    
    if not expect_json:
        return initial_response
        
    try:
        # Tenta sanitizar antes de dar load
        clean_text = initial_response.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text.split("```json")[1]
        if clean_text.endswith("```"):
            clean_text = clean_text.rsplit("```", 1)[0]
        return json.loads(clean_text.strip())
    except json.JSONDecodeError as e:
        print(f"Erro no parsing do JSON inicial: {e}")
        # Retry explicitly asking for valid JSON
        retry_prompt = f"{user_message}\n\nA sua resposta anterior não foi um JSON válido. Por favor, retorne APENAS o JSON válido:\n{initial_response}"
        retry_response = do_call(retry_prompt)
        
        try:
            clean_text = retry_response.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text.split("```json")[1]
            if clean_text.endswith("```"):
                clean_text = clean_text.rsplit("```", 1)[0]
            return json.loads(clean_text.strip())
        except json.JSONDecodeError:
            raise ValueError(f"Não foi possível parsear a resposta do LLM para JSON após retry. Retorno cru: {retry_response}")

def call_claude_with_reflection(
    system_prompt: str,
    user_message: str,
    critique_prompt: str
) -> str:
    """
    Padrão Redator SOPs. 
    (1) Escreve inicial
    (2) Critica a si próprio
    (3) Reescreve aplicando críticas
    """
    model = "claude-3-5-sonnet-20241022"
    
    # 1. Primeira passagem
    initial_draft = call_claude(
        system_prompt=system_prompt,
        user_message=user_message,
        model=model,
        temperature=0.3
    )
    
    # 2. Reflexão e Revisão
    revision_prompt = f"""
    Abaixo está o esboço de um documento:
    ---
    {initial_draft}
    ---
    {critique_prompt}
    Reescreva o documento completo corrigindo todos os pontos falhos.
    """
    
    final_version = call_claude(
        system_prompt="Você é um revisor implacável de processos.",
        user_message=revision_prompt,
        model=model,
        temperature=0.3
    )
    
    return final_version
