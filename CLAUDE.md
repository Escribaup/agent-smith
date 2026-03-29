# Agente Smith — iDVL Gestão

## O que este projeto faz
Sistema multi-agente n8n que conduz um projeto de profissionalização de gestão
para um escritório contábil (iDVL), operando via WhatsApp com o CEO e equipe.

## Arquitetura (Divisão do Trabalho — Adam Smith)
- Orquestrador: coordena, nunca executa diretamente
- 5 sub-agentes especializados: Entrevistador, Mapeador, Redator SOPs, Analista, Follow-up
- Memória primária: PostgreSQL banco smith_project (62.171.191.4:5432)
- Memória de documentos: Google Drive (SOPs, relatórios, mapas)
- Comunicação: Z-API para WhatsApp

## Padrões usados
- Todos os workflows n8n estão em `workflows/` como JSON exportável
- Todas as ferramentas Python estão em `tools/`
- Todos os system prompts estão em `prompts/` como .md
- Variáveis de ambiente em `.env` (nunca hardcode credenciais)

## Estado atual do projeto
Ver `contexto.json` no Google Drive para fase atual e dados coletados.

## Regras de implementação
1. Nunca hardcode nenhuma credencial
2. Sempre valide JSON retornado pelo LLM antes de salvar
3. Sempre verifique contexto.json antes de fazer qualquer pergunta
4. Toda mensagem WhatsApp ao CEO: máximo 5 linhas, sem markdown
5. Toda aprovação de fase requer `fase.aprovada === true` no contexto
