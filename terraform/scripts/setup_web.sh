#!/bin/bash
set -e
exec > >(tee -a /var/log/golden_ami_build.log /var/log/cloud-init-output.log) 2>&1
echo "=== [1/5] INICIANDO BUILD DA GOLDEN AMI: WEB (FASTAPI + REACT) ==="

# 1. Atualizar SO e instalar dependencias basicas
echo "=== [2/5] Instalando dependencias basicas e Node.js 20 LTS ==="
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    git python3 python3-pip python3-venv curl libpq-dev

curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 2. Clonar código do repositório
echo "=== [3/5] Clonando repositório e preparando virtualenv ==="
sudo mkdir -p /opt/sqlarena && cd /opt
sudo rm -rf sqlarena
git clone -b main https://github.com/ggustavo/SQLArena.git /opt/sqlarena
cd /opt/sqlarena

python3 -m venv app/.venv
source app/.venv/bin/activate
pip install --upgrade pip
pip install -r app/requirements.txt

# 3. Compilar o Frontend React (Vite SPA)
echo "=== [4/5] Instalando pacotes e compilando frontend React ==="
cd /opt/sqlarena/frontend
export VITE_API_URL=/api
npm install
npm run build

# 4. Criar template de serviço systemd para a API Web
cat <<EOT | sudo tee /etc/systemd/system/sqlarena-web.service
[Unit]
Description=SQLArena Web API and Frontend Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sqlarena
EnvironmentFile=/opt/sqlarena/app/.env
ExecStart=/opt/sqlarena/app/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOT

sudo systemctl daemon-reload
sudo systemctl enable sqlarena-web.service

# Limpeza de logs e caches para deixar a AMI limpa
sudo rm -rf /root/.cache /root/.npm /home/ubuntu/.cache /home/ubuntu/.npm /tmp/*

echo "=== [5/5] BUILD CONCLUÍDO COM SUCESSO! DESLIGANDO PARA SNAPSHOT ==="
sync
sudo shutdown -h now
