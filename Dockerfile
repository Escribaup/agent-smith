FROM python:3.12-slim

WORKDIR /app

# Instala ferramentas necessárias do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código
COPY ./tools ./tools

# Expõe a porta 8000 (FastAPI padrão)
EXPOSE 8000

# Comando para rodar a API
CMD ["uvicorn", "tools.api:app", "--host", "0.0.0.0", "--port", "8000"]
