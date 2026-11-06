# ==============================================================================
# Dockerfile do Backend e Worker (FastAPI + Worker Kafka/MinIO/Postgres)
# ==============================================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace \
    APP_PORT=8000

WORKDIR /workspace

# Instala dependências de sistema necessárias para psycopg2, healthchecks e compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python aproveitando cache de camadas do Docker
COPY app/requirements.txt /workspace/app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /workspace/app/requirements.txt

# Copia o código-fonte do backend/worker
COPY app /workspace/app

# Configura o script de entrypoint garantindo quebras de linha LF (Unix)
COPY app/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
