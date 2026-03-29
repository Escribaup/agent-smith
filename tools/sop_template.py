try:
    from tools import llm_client
except ImportError:
    import llm_client

def render_sop(data: dict) -> str:
    """
    Renderiza SOP em markdown a partir de dict.
    Campos esperados:
    - processo, objetivo, responsavel, inputs
    - passos (lista de dict com numero, acao, quem, tempo)
    - criterio_qualidade, se_travar, versao, data
    """
    md = [
        f"# {data.get('processo', 'Processo sem nome')} — SOP {data.get('versao', 'v1')}",
        "",
        f"**Data de emissão:** {(data.get('data', ''))}",
        "",
        "## Objetivo",
        f"{data.get('objetivo', '')}",
        "",
        "## Responsável",
        f"{data.get('responsavel', '')}",
        "",
        "## Quando executar",
        f"{data.get('gatilho', 'Sem gatilho definido.')}",
        "",
        "## Inputs necessários"
    ]
    
    for inp in data.get('inputs', []):
        md.append(f"- {inp}")
        
    md.extend(["", "## Passo a passo"])
    
    for step in data.get('passos', []):
        numero = step.get('numero', 0)
        acao = step.get('acao', '')
        quem = step.get('quem', '')
        tempo = step.get('tempo', '')
        md.append(f"{numero}. {acao} — **{quem}** — *{tempo}*")
        
    md.extend([
        "",
        "## Critério de qualidade",
        f"{data.get('criterio_qualidade', '')}",
        "",
        "## O que fazer se travar"
    ])
    
    for s in data.get('se_travar', []):
        md.append(f"- {s}")
        
    md.extend([
        "",
        "## Histórico de versões",
        "| Versão | Data | Alteração |",
        "|--------|------|-----------|",
        f"| {data.get('versao', 'v1')} | {(data.get('data', ''))} | Criação inicial |"
    ])
    
    return "\n".join(md)

def extract_sop_data_from_interview(interview_text: str) -> dict:
    """
    Usa LLM para abstrair e estruturar um JSON compatível com o SOP.
    """
    prompt_sys = "Extraia do texto livre os passos concretos operacionais para um procedimento documentado em formato SOP. Responda ESTRITAMENTE em JSON sem Markdown markdown, chaves validas: processo, objetivo, responsavel, gatilho, inputs(array), passos(array de keys numero, acao, quem, tempo), criterio_qualidade, se_travar(array), versao, data."
    
    return llm_client.call_claude(
        system_prompt=prompt_sys,
        user_message=interview_text,
        expect_json=True
    )
