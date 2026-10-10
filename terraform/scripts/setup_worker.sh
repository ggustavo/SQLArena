#!/bin/bash
set -e
exec > >(tee -a /var/log/golden_ami_build.log /var/log/cloud-init-output.log) 2>&1
echo "=== [1/5] INICIANDO BUILD DA GOLDEN AMI: WORKER SQLARENA ==="

# 1. Atualizar SO e instalar dependencias basicas e PostgreSQL para a Sandbox
echo "=== [2/5] Instalando pacotes do sistema (PostgreSQL + Python) ==="
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    git python3 python3-pip python3-venv libpq-dev postgresql postgresql-contrib curl

# 2. Configurar PostgreSQL Sandbox Local
echo "=== [3/5] Configurando PostgreSQL Sandbox Local ==="
sudo systemctl enable postgresql
sudo systemctl start postgresql
sudo -u postgres psql -c "CREATE USER sandbox WITH PASSWORD 'sandboxpass';" || true
sudo -u postgres psql -c "CREATE DATABASE sandbox_db OWNER sandbox;" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE sandbox_db TO sandbox;" || true

# 3. Clonar código e preparar ambiente virtual Python
echo "=== [4/5] Clonando repositório e instalando dependências Python ==="
sudo mkdir -p /opt/sqlarena && cd /opt
sudo rm -rf sqlarena
git clone -b main https://github.com/ggustavo/SQLArena.git /opt/sqlarena
cd /opt/sqlarena

python3 -m venv app/.venv
source app/.venv/bin/activate
pip install --upgrade pip
pip install -r app/requirements.txt

# 4. Criar template de serviço systemd para o Worker
cat <<EOT | sudo tee /etc/systemd/system/sqlarena-worker.service
[Unit]
Description=SQLArena SQS Submission Worker Service
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sqlarena
EnvironmentFile=/opt/sqlarena/app/.env
ExecStart=/opt/sqlarena/app/.venv/bin/python app/worker/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOT

sudo systemctl daemon-reload
sudo systemctl enable sqlarena-worker.service

# Limpeza de logs e caches para deixar a AMI limpa
sudo rm -rf /root/.cache /home/ubuntu/.cache /tmp/*

echo "=== [5/5] BUILD CONCLUÍDO COM SUCESSO! DESLIGANDO PARA SNAPSHOT ==="
sync
sudo shutdown -h now
