# SQLArena - Infraestrutura & Ambiente de Desenvolvimento

Este projeto foi estruturado para suportar o desenvolvimento e testes locais com **Ministack** (emulador de serviços AWS via Docker) e permitir a migração transparente de toda a infraestrutura para a **AWS real** utilizando **Terraform (Infraestrutura como Código - IaC)**.

---

## 1. Estrutura do Projeto

```text
SQLArena/
├── ministack/                   # Configuração e persistência do emulador local
│   ├── docker-compose.yml       # Orquestração do ministack
│   └── data/                    # Dados locais persistidos (S3, logs, etc.)
│
├── terraform/                   # Infraestrutura como Código
│   ├── providers.tf             # Configuração do provedor AWS e endpoints locais
│   ├── variables.tf             # Variáveis de ambiente e configuração
│   ├── outputs.tf               # Dados de saída (URLs de conexão, IDs de recursos)
│   ├── rds.tf                   # Declaração da instância do banco de dados (RDS PostgreSQL)
│   ├── elasticache.tf           # Declaração do cluster Redis (ElastiCache)
│   ├── ec2.tf                   # Declaração da máquina virtual e firewall (EC2)
│   ├── sqs.tf                   # Declaração da fila principal e DLQ (SQS)
│   └── envs/
│       ├── local.tfvars         # Parâmetros para rodar apontando para o Ministack
│       └── aws.tfvars           # Parâmetros para deploy na AWS de verdade
│
└── app/                         # Código da aplicação, módulos e configurações
    ├── .env                     # Variáveis de ambiente ativas (ignorado pelo Git)
    ├── .env.example             # Modelo documentado das variáveis de ambiente
    ├── requirements.txt         # Dependências Python centralizadas
    ├── backend/                 # Código da API backend
    └── sqs/                     # Módulo e testes do Amazon SQS
        ├── queue_manager.py     # Funções de envio, consumo, purge e DLQ
        └── main.py              # Script de teste e demonstração da fila
```

---

## 2. Pré-requisitos & Instalação

### 1. Docker
* Certifique-se de que o **Docker** (ou Docker Desktop no macOS/Windows) esteja instalado e em execução.

---

### 2. Terraform CLI

Instale o Terraform de acordo com o seu sistema operacional:

#### Linux (Ubuntu / Debian)
```bash
sudo apt-get update && sudo apt-get install -y gnupg software-properties-common curl
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt-get update && sudo apt-get install -y terraform
```

#### Linux (Fedora / RHEL / CentOS)
```bash
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://rpm.releases.hashicorp.com/fedora/hashicorp.repo
sudo dnf -y install terraform
```

#### macOS (via Homebrew)
```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```

#### Windows (via Winget ou Chocolatey)
```powershell
# Via Winget:
winget install HashiCorp.Terraform

# Ou via Chocolatey:
choco install terraform
```

---

### Validar a Instalação
Em qualquer sistema operacional, abra um novo terminal e execute:
```bash
terraform version
```

---

## 3. Como Subir e Gerenciar o Ministack

O Ministack emula as APIs da AWS localmente e se comunica com o Docker host para criar os containers dos serviços (como PostgreSQL para o RDS e Redis para o ElastiCache).

### Iniciar o Ministack:
```bash
cd ministack
docker compose up -d
```

### Verificar o status:
```bash
# Ver se o container está rodando:
docker ps

# Acompanhar os logs do Ministack em tempo real:
docker compose logs -f
```

### Parar o Ministack:
```bash
docker compose down
```

---

## 4. Ciclo de Comandos do Terraform no Dia a Dia

Os comandos a seguir são **idênticos em qualquer sistema operacional** (Linux, macOS ou Windows).

Navegue até o diretório `terraform/`:
```bash
cd terraform
```

### 1. Inicialização (`init`)
Baixa o provider oficial da AWS e prepara o diretório de trabalho:
```bash
terraform init
```

### 2. Planejamento (`plan`)
Mostra um resumo detalhado de tudo que será criado, modificado ou destruído sem aplicar nenhuma alteração:
```bash
terraform plan -var-file="envs/local.tfvars"
```

### 3. Aplicação (`apply`)
Cria os recursos de fato (RDS, ElastiCache, EC2, SQS):
```bash
terraform apply -var-file="envs/local.tfvars"
```
*(Digite `yes` quando solicitado, ou adicione a flag `-auto-approve`)*

### 4. Destruição (`destroy`)
Para remover todos os recursos criados e resetar o ambiente:
```bash
terraform destroy -var-file="envs/local.tfvars"
```

---

## 5. Configuração do Ambiente Python (Aplicação & Testes)

Para executar os scripts da pasta `app/` (como o teste do SQS ou o desenvolvimento do backend):

### 1. Criar o Ambiente Virtual (`venv`)
Na raiz do projeto, execute:
```bash
python -m venv .venv
```

### 2. Ativar o Ambiente Virtual

* **Linux / macOS:**
  ```bash
  source .venv/bin/activate
  ```

* **Windows (PowerShell):**
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
  *(Se o PowerShell bloquear a execução de scripts, rode antes uma vez: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*

* **Windows (Prompt de Comando / CMD):**
  ```cmd
  .venv\Scripts\activate.bat
  ```

---

### 3. Instalar as Dependências
Com o ambiente virtual ativado, instale os pacotes necessários:
```bash
pip install -r requirements.txt
```

---

### 4. Configurar as Variáveis de Ambiente
O projeto já conta com o arquivo [`app/.env`](app/.env) configurado para desenvolvimento local. Caso precise recriá-lo a partir do modelo:

* **Linux / macOS:**
  ```bash
  cp app/.env.example app/.env
  ```
* **Windows (PowerShell):**
  ```powershell
  Copy-Item app\.env.example app\.env
  ```

---

### 5. Executar os Testes do SQS
Com o Ministack em execução e a infraestrutura aplicada pelo Terraform, execute:
```bash
python app/sqs/main.py
```

---

## 6. Como Funciona o EC2 (Local vs Nuvem)

### 1. No Ambiente Local (Ministack)
No desenvolvimento local, o Ministack **emula a API do EC2** (gerando IDs e metadados para que o Terraform funcione sem erros), mas **não sobe uma máquina virtual**:
* Os containers Docker ativos são os que exigem serviços de dados reais: **RDS (Postgres)**, **ElastiCache (Redis)** e o gateway do **Ministack (SQS/APIs)**.
* **O seu ambiente de execução do backend é a sua própria máquina local:** você roda a sua aplicação no seu terminal com o `.venv` ativo, conectando-se aos serviços do Docker através das portas expostas (`localhost:15432` para banco, `localhost:16379` para redis e `localhost:4566` para SQS).

---

### 2. Na AWS Real (Nuvem)
Quando você aplicar o Terraform na nuvem da Amazon, a AWS criará um servidor virtual real (instância EC2). Você poderá acessar o terminal dessa máquina das seguintes formas:


#### Opção A: Conexão via SSH (Tradicional)
Para conectar via SSH padrão, certifique-se de ter uma chave `.pem` configurada:

1. **Ajustar as permissões da chave privada (apenas Linux/macOS):**
   ```bash
   chmod 400 minha-chave.pem
   ```

2. **Conectar pelo terminal usando o IP público:**
   *(O IP público é exibido pelo Terraform no output `ec2_public_ip` após o `terraform apply`)*
   ```bash
   # Se a imagem for Ubuntu:
   ssh -i /caminho/para/minha-chave.pem ubuntu@<IP_PUBLICO_DA_EC2>

   # Se a imagem for Amazon Linux 2023:
   ssh -i /caminho/para/minha-chave.pem ec2-user@<IP_PUBLICO_DA_EC2>
   ```

> [!NOTE]
> Para usar SSH na AWS real, lembre-se de associar o parâmetro `key_name` na declaração da `aws_instance` no arquivo `terraform/ec2.tf`.

---

#### Opção B: EC2 Instance Connect (Navegador ou CLI)
Permite conectar sem precisar gerenciar arquivos de chave `.pem`:

* **Pelo Console da AWS:**
  Acesse **EC2** > **Instâncias** > selecione sua máquina > clique no botão **Conectar** > aba **EC2 Instance Connect** > **Conectar**.

* **Pelo terminal (com AWS CLI instalada):**
  ```bash
  aws ec2-instance-connect ssh --instance-id <ID_DA_INSTANCIA>
  ```

---

#### Opção C: AWS Systems Manager (SSM Session Manager - Mais Seguro)
A forma recomendada em produção pela AWS, pois **não exige liberar a porta 22 (SSH) na internet** nem gerenciar chaves:

```bash
aws ssm start-session --target <ID_DA_INSTANCIA>
```

