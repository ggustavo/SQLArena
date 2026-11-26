#!/bin/sh
set -e

export PYTHONPATH="/workspace"

echo "============================================================"
echo "🚀 Inicializando Container SQLArena (${SERVICE_ROLE:-backend})"
echo "============================================================"

# Se RUN_SEED=true (padrão no container Backend), aguarda o Postgres e executa o seed inicial
if [ "${RUN_SEED}" = "true" ]; then
    echo "[Entrypoint] Verificando disponibilidade do banco PostgreSQL e executando Seed inicial..."
    python -c "
import time, os, psycopg2
db_url = os.getenv('DATABASE_URL', '').replace('postgresql+psycopg2://', 'postgresql://')
for i in range(30):
    try:
        conn = psycopg2.connect(db_url)
        conn.close()
        print('[Entrypoint] ✓ PostgreSQL Principal disponível!')
        break
    except Exception as e:
        print(f'[Entrypoint] Aguardando PostgreSQL ({i+1}/30): {e}')
        time.sleep(2)
"
    python app/database/seed.py --if-empty
fi

# Se for o Worker, aguarda o PostgreSQL Sandbox local estar aceitando conexões
if [ "${SERVICE_ROLE}" = "worker" ]; then
    echo "[Entrypoint] Aguardando disponibilidade do PostgreSQL Sandbox..."
    python -c "
import time, os, psycopg2
sb_url = (os.getenv('SANDBOX_DATABASE_URL') or os.getenv('DATABASE_URL', '')).replace('postgresql+psycopg2://', 'postgresql://')
for i in range(30):
    try:
        conn = psycopg2.connect(sb_url)
        conn.close()
        print('[Entrypoint] ✓ PostgreSQL Sandbox disponível!')
        break
    except Exception as e:
        print(f'[Entrypoint] Aguardando PostgreSQL Sandbox ({i+1}/30): {e}')
        time.sleep(2)
"
fi

exec "$@"
