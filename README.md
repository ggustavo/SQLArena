# ⚔️ SQLArena - Plataforma Distribuída de Ensino e Avaliação de SQL

Plataforma elástica e isolada para prática e avaliação automatizada de consultas SQL em ambiente real **PostgreSQL 16** com isolamento por schemas (Sandbox), mensageria assíncrona via **Apache Kafka**, armazenamento de objetos compatível com S3 via **MinIO**, cache e rate-limit via **Redis**, auditoria NoSQL no **Amazon DynamoDB (AWS)** e orquestração completa com **Docker Compose**, **Kubernetes (Pods Multi-Container + HPA)** e **Terraform**.

---

## 🏛️ Arquitetura do Sistema (Containers, Pods K8s & AWS DynamoDB)

<p align="center">
  <img src="docs/arquitetura.png" alt="Arquitetura do Sistema SQLArena" width="100%" />
</p>

### Componentes e Substituições da Arquitetura

| Serviço / Camada | Tecnologia Atual | Função na Arquitetura SQLArena |
| :--- | :--- | :--- |
| **1. Banco NoSQL (Mantido na AWS)** | **Amazon DynamoDB** | Permanece como serviço gerenciado na nuvem AWS. Armazena de forma imutável o histórico de submissões/erros (`sqlarena-submissions-log`) e a auditoria de ações administrativas (`sqlarena-crud-actions-log`). |
| **2. Banco Relacional Principal** | **Docker / K8s PostgreSQL 16** *(Substitui o Amazon RDS)* | Container `postgres:16-alpine` com volume persistente gerenciado por nós. Armazena usuários, categorias N:N, metadados das questões e pontuação consolidada (+10 XP). |
| **3. Armazenamento de Arquivos** | **Docker / K8s MinIO** *(Substitui o Amazon S3)* | Container `minio/minio:latest` compatível com a API S3 (`boto3`). Armazena os scripts SQL puros de cada questão (`schema.sql`, `data.sql`, `answer.sql`) no bucket `sqlarena-questions-bucket` e os avatares dos usuários. |
| **4. Fila de Mensagens Assíncrona** | **Docker / K8s Apache Kafka** *(Substitui o Amazon SQS)* | Container `apache/kafka:3.8.0` em modo **KRaft** (sem Zookeeper). Gerencia o tópico particionado `sqlarena-submissions-queue` (3 partições para paralelismo dos Workers) e a Dead Letter Queue (`sqlarena-submissions-queue-dlq`). |
| **5. Cache & Rate Limit** | **Docker / K8s Redis 7** *(Substitui o ElastiCache)* | Container `redis:7-alpine`. Controla o Rate Limit de 5 segundos por aluno, cache de ranking/questões e status em tempo real para polling. |
| **6. Imagem do Backend & Worker** | **`app/Dockerfile`** | Imagem Python 3.11 unificada que executa a API REST **FastAPI** (com seed automático inteligente `--if-empty`) e o **Worker Assíncrono**. |
| **7. Imagem do Frontend** | **`frontend/Dockerfile`** | Build Multi-Stage: compila o **React 19 + Vite + Tailwind CSS v4** com Node 20 e serve via **Nginx 1.27 Alpine** com Reverse Proxy integrado para `/api`. |

---

## 🧩 Arquitetura de Pods Multi-Container no Kubernetes (Sidecar Pattern)

Antes tínhamos duas Golden AMIs na AWS (uma para Web e outra para o Worker com Postgres local). No **Kubernetes**, convertemos essa exata topologia em **dois Deployments de Pods Multi-Container**, aproveitando o fato de que containers dentro do mesmo Pod compartilham a mesma interface de rede (`localhost` / `127.0.0.1`):

```mermaid
flowchart TB
    subgraph AWS["☁️ Nuvem AWS"]
        Dynamo[("📄 Amazon DynamoDB\n(Submissões & Auditoria CRUD)")]
    end

    subgraph K8S["☸️ Cluster Kubernetes (Amazon EKS) / Docker Compose"]
        NP["🌐 Service NodePort (30080)\nPonto de Entrada Público"]
        CIP["🔗 Service ClusterIP (sqlarena-web-clusterip:8000)\nComunicação Interna"]

        subgraph PodWeb["📦 POD 1: Deployment 'sqlarena-web' (Escalável via HPA)"]
            FE["🖥️ Container Frontend\n(React SPA + Nginx :80)"]
            BE["⚙️ Container Backend\n(FastAPI :8000)"]
            FE -- "Reverse Proxy via localhost\nhttp://127.0.0.1:8000/api" --> BE
        end

        subgraph PodWorker["📦 POD 2: Deployment 'sqlarena-worker' (Escalável via HPA)"]
            WK["⚡ Container Worker\n(Python Consumer)"]
            PGSB[("🐘 Container Postgres Sandbox\n(Sidecar Local 127.0.0.1:5432)")]
            WK -- "Executa SQL do Aluno em\n127.0.0.1:5432 (Isolado)" --> PGSB
        end

        subgraph InfraServices["🗄️ Serviços de Dados no Cluster (Services ClusterIP)"]
            PGMain[("🐘 Postgres Principal\n(postgres-service:5432)\n[Substitui RDS]")]
            MinIO[("🪣 MinIO Storage\n(minio-service:9000)\n[Substitui S3]")]
            Kafka[["📬 Apache Kafka KRaft\n(kafka-service:9092)\n[Substitui SQS]"]]
            Redis[("🏎️ Redis Cache\n(redis-service:6379)\n[Substitui ElastiCache]")]
        end

        NP --> FE
        BE --> PGMain
        BE --> Redis
        BE --> MinIO
        BE -- "Publica Submissão" --> Kafka
        Kafka -- "Consome (Consumer Group)" --> WK
        WK -- "Lazy-Load SQL" --> MinIO
        WK -- "Callback HTTP Resultado" --> CIP
        CIP --> BE
    end

    BE <-->|"boto3 (Secrets K8s / LabRole)"| Dynamo
```

1. **Pod 1 — `sqlarena-web` (`k8s/07-web-pod.yaml`):**
   * Roda o **Frontend (Nginx)** + **Backend (FastAPI)** juntos no mesmo Pod.
   * O Nginx serve o React na porta `80` e encaminha `/api/*` diretamente para `http://127.0.0.1:8000` (loopback dentro do Pod, com latência zero!).
   * Exposto externamente por um Service **NodePort** (`30080`) e internamente por um Service **ClusterIP** (`sqlarena-web-clusterip:8000`).
2. **Pod 2 — `sqlarena-worker` (`k8s/08-worker-pod.yaml`):**
   * Roda o **Worker Python** + **PostgreSQL 16 Sandbox** juntos no mesmo Pod.
   * O Worker conecta em `postgresql://sandbox:sandboxpass@127.0.0.1:5432/sandbox_db` e usa um volume efêmero (`emptyDir`).
   * **Escalabilidade Horizontal Perfeita (`k8s/09-hpa.yaml`):** Quando o **HorizontalPodAutoscaler (HPA)** escala o `sqlarena-worker` de 1 para 4 Pods sob carga de CPU, cada novo Pod já nasce com seu próprio banco PostgreSQL Sandbox exclusivo e entra automaticamente no Consumer Group do **Kafka** para dividir o consumo das partições!

---

## 📂 Estrutura e Organização do Projeto

```text
SQLArena/
├── app/
│   ├── Dockerfile              # Imagem Docker do Backend (FastAPI) e do Worker
│   ├── entrypoint.sh           # Script de boot com wait de banco e seed automático (--if-empty)
│   ├── api/                    # Rotas REST (FastAPI): auth, questions, submissions, audit, users, ranking
│   ├── cache/                  # Cliente Redis (Rate Limit de 5s e cache de status/ranking)
│   ├── database/               # PostgreSQL Principal: SQLAlchemy, models.py, seed.py e validator.py
│   ├── dynamodb/               # Cliente oficial do Amazon DynamoDB (AWS)
│   ├── kafka/                  # Produtor, Consumidor e Admin do Apache Kafka (substituindo SQS)
│   ├── s3/                     # Cliente MinIO compatível com S3 (substituindo Amazon S3)
│   ├── sqs/                    # Adaptador compatível apontando para o KafkaQueueManager
│   ├── worker/                 # Motor de avaliação isolado em PostgreSQL Sandbox
│   ├── config.py               # Configurações centralizadas (Pydantic Settings)
│   └── main.py                 # Ponto de entrada FastAPI
├── frontend/
│   ├── Dockerfile              # Imagem Docker Multi-Stage (Node 20 Build -> Nginx 1.27 Alpine)
│   ├── nginx.conf.template     # Configuração do Nginx com Reverse Proxy dinâmico para /api
│   └── src/                    # Código-fonte React 19, Tailwind CSS v4 e Monaco Editor
├── k8s/                        # Manifestos Kubernetes (Deployments, Services ClusterIP/NodePort, Secrets, HPA)
│   ├── 01-configmap.yaml       # Variáveis de ambiente não-sensíveis
│   ├── 02-secrets.yaml         # Credenciais seguras (Postgres, MinIO, JWT e chaves AWS DynamoDB)
│   ├── 03-postgres-main.yaml   # Deployment + PVC + Service ClusterIP do Postgres Principal
│   ├── 04-redis.yaml           # Deployment + Service ClusterIP do Redis
│   ├── 05-minio.yaml           # Deployment + PVC + Service ClusterIP e NodePort (30901) do MinIO
│   ├── 06-kafka.yaml           # Deployment + Service ClusterIP do Apache Kafka (KRaft)
│   ├── 07-web-pod.yaml         # POD 1 (Frontend + Backend) + Services ClusterIP e NodePort (30080)
│   ├── 08-worker-pod.yaml      # POD 2 (Worker + Postgres Sandbox Sidecar) + Service ClusterIP
│   └── 09-hpa.yaml             # HorizontalPodAutoscaler (HPA) para escalar Web Pods e Worker Pods
├── terraform/                  # Infraestrutura como Código na AWS organizada em 2 Modos
│   ├── README.md               # Documentação detalhada da organização do Terraform
│   ├── envs/
│   │   ├── credentials.tfvars.example # Modelo para chaves AWS / AWS Academy
│   │   ├── modo1-eks.tfvars           # Variáveis para Modo 1 (100% EKS + DynamoDB)
│   │   ├── modo2-ec2-compose.tfvars   # Variáveis para Modo 2 (1 EC2 com Docker Compose + DynamoDB)
│   │   └── local.tfvars               # Variáveis para emulador local
│   ├── modules/                # Módulos reutilizáveis: dynamodb, vpc, eks, ec2-compose
│   ├── modo1-eks/              # Stack dedicada para Modo 1 (100% EKS + DynamoDB)
│   ├── modo2-ec2-compose/      # Stack dedicada para Modo 2 (1 EC2 Docker Compose + DynamoDB)
│   └── main.tf                 # Orquestrador raiz
├── docker-compose.yml          # Orquestração completa dos 8 containers com 1 comando
└── .env.example                # Modelo de variáveis de ambiente para o Docker Compose
```

---

# 🐳 GUIA 1: EXECUÇÃO COM DOCKER E DOCKER COMPOSE (Local ou em EC2 na AWS)

Com o novo [`docker-compose.yml`](docker-compose.yml) na raiz do projeto, **todos os serviços** (Frontend, Backend, Worker, Postgres Principal, Postgres Sandbox, MinIO, Kafka e Redis) sobem juntos com um único comando e se conectam ao **Amazon DynamoDB** da AWS.

### Passo 1: Configurar o arquivo `.env` com suas Credenciais AWS (para o DynamoDB)
Na raiz do projeto (`SQLArena/`), copie o arquivo de exemplo `.env.example` para `.env`:

```powershell
# No Windows (PowerShell):
Copy-Item .env.example .env

# No Linux / EC2:
cp .env.example .env
```

Abra o arquivo `.env` e preencha suas credenciais da AWS (do seu **AWS Academy Learner Lab -> AWS Details -> AWS CLI**) para que o Backend grave e consulte nas tabelas do **Amazon DynamoDB**:

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=ASIA...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=IQoJb3JpZ2luX2VjE...
DYNAMODB_ENDPOINT_URL=
```
*(💡 **Dica para teste 100% offline no PC:** Caso queira testar no seu computador sem internet/sem conta AWS aberta, basta subir o Ministack na porta 4566 ou definir `DYNAMODB_ENDPOINT_URL=http://host.docker.internal:4566` com chaves `test`).*

### Passo 2: Construir as Imagens e Iniciar Todos os Containers
Na raiz do projeto (`SQLArena/`), execute:

```powershell
docker compose up -d --build
```

> ⚙️ **O que acontece automaticamente quando você roda esse comando?**
> 1. O Docker inicia os containers de infraestrutura com *healthchecks*:
>    * `sqlarena-postgres` (PostgreSQL 16 Principal na porta `15432`)
>    * `sqlarena-postgres-sandbox` (PostgreSQL 16 Sandbox do Worker na porta `15433`)
>    * `sqlarena-redis` (Redis 7 na porta `16379`)
>    * `sqlarena-minio` (MinIO S3 API na porta `9000` e Console Web na porta `9001`)
>    * `sqlarena-kafka` (Apache Kafka KRaft na porta `9092`)
> 2. O container `sqlarena-backend` constrói a imagem a partir de [`app/Dockerfile`](app/Dockerfile), executa automaticamente o `seed.py --if-empty` (criando as tabelas no Postgres, o bucket e os 63 arquivos `.sql` das 21 questões no **MinIO**, os tópicos no **Kafka** e as tabelas no **AWS DynamoDB**) e inicia a API FastAPI na porta `8000`.
> 3. O container `sqlarena-worker` inicia o consumidor do **Kafka**, pronto para baixar os scripts do **MinIO** e avaliar consultas no `sqlarena-postgres-sandbox`.
> 4. O container `sqlarena-frontend` constrói a imagem a partir de [`frontend/Dockerfile`](frontend/Dockerfile) e inicia o Nginx nas portas `80` e `5173`.

### Passo 3: Acessar os Serviços
* 🚀 **Aplicação Web Completa (Frontend + API):** [http://localhost](http://localhost) ou [http://localhost:5173](http://localhost:5173) *(na EC2: `http://<IP_PUBLICO_EC2>`)*
* 📖 **Documentação Swagger UI (FastAPI):** [http://localhost:8000/docs](http://localhost:8000/docs)
* 🪣 **Console Web do MinIO (Visualizar Arquivos SQL):** [http://localhost:9001](http://localhost:9001)
  * **Usuário:** `minioadmin` | **Senha:** `minioadmin123`

### Comandos Úteis do Docker Compose
```powershell
# Ver o status de todos os containers:
docker compose ps

# Acompanhar os logs do Backend e do Worker em tempo real:
docker compose logs -f backend worker

# Parar e remover os containers (mantendo volumes):
docker compose down

# Parar e apagar todos os volumes (reset completo):
docker compose down -v
```

---

# ☁️ GUIA 2: IMPLANTAÇÃO NA AWS COM TERRAFORM (2 Modos Organizados)

A pasta [`terraform/`](terraform/) foi organizada em módulos limpos (`dynamodb`, `vpc`, `ec2-compose` e `eks`) para suportar **duas formas de implantação na AWS**, mantendo sempre o **Amazon DynamoDB** na AWS:

1. **Modo 2 (`ec2_compose`):** Provisiona as tabelas do **DynamoDB** + **1 única instância EC2 (`t3.medium`)** que já instala Docker e Docker Compose automaticamente no boot (`user_data`), clona o repositório e sobe toda a pilha com `docker compose up -d --build`.
2. **Modo 1 (`eks`):** Provisiona as tabelas do **DynamoDB** + repositórios **Amazon ECR** + cluster Kubernetes gerenciado **Amazon EKS** com Worker Nodes para rodar nossos Pods escaláveis (`k8s/`).

---

## Preparação Comum: Configurar Credenciais do AWS Academy
1. No seu **AWS Academy Learner Lab**, clique em **Start Lab** e depois em **AWS Details -> AWS CLI**.
2. Copie o modelo `terraform/envs/credentials.tfvars.example` para `terraform/envs/credentials.tfvars` (este arquivo é ignorado pelo Git):

```hcl
aws_access_key    = "ASIA..."
aws_secret_key    = "..."
aws_session_token = "IQoJb3JpZ2luX2VjE..."
```

---

## 🅰️ MODO 2 NA AWS: Apenas Docker e Docker Compose em 1 EC2 + DynamoDB

Ideal para subir toda a aplicação rapidamente em uma única máquina EC2 na AWS gastando o mínimo de créditos do laboratório:

```powershell
cd terraform
terraform init
terraform apply -var-file="envs/modo2-ec2-compose.tfvars" -var-file="envs/credentials.tfvars"
```
*(Alternativamente, você também pode entrar na pasta dedicada `cd terraform/modo2-ec2-compose`, rodar `terraform init` e `terraform apply -var-file="../envs/credentials.tfvars"`).*

### Como acessar após o `terraform apply`:
O Terraform exibirá no terminal os links prontos:
* **`modo2_frontend_url`** = `http://<IP_PUBLICO_EC2>` *(Plataforma SQLArena)*
* **`modo2_swagger_url`** = `http://<IP_PUBLICO_EC2>:8000/docs` *(Swagger UI)*
* **`modo2_minio_console_url`** = `http://<IP_PUBLICO_EC2>:9001` *(Painel do MinIO)*

*(Aguarde cerca de 2 a 3 minutos após a criação da EC2 para que o script de `user_data` conclua a instalação do Docker e o build inicial das imagens. Você pode acompanhar via SSH com `tail -f /var/log/cloud-init-output.log`).*

---

## 🅱️ MODO 1 NA AWS: 100% Amazon EKS (Kubernetes) + DynamoDB

Provisiona um cluster Kubernetes real (**Amazon EKS**), repositórios de imagem (**Amazon ECR**) e as tabelas do **Amazon DynamoDB**:

### Passo 1: Provisionar o Cluster EKS e o DynamoDB via Terraform
```powershell
cd terraform
terraform init
terraform apply -var-file="envs/modo1-eks.tfvars" -var-file="envs/credentials.tfvars"
```
*(Ou diretamente na pasta dedicada: `cd terraform/modo1-eks`, `terraform init` e `terraform apply -var-file="../envs/credentials.tfvars"`).*

### Passo 2: Conectar seu `kubectl` ao Cluster EKS criado
Copie e execute o comando retornado no output `modo1_eks_kubeconfig_command`:
```powershell
aws eks update-kubeconfig --region us-east-1 --name sqlarena-eks
kubectl get nodes
```

### Passo 3: Enviar as Imagens Docker para o Amazon ECR (ou Docker Hub)
Use as URLs retornadas nos outputs `modo1_ecr_backend_url` e `modo1_ecr_frontend_url`:
```powershell
# 1. Login no Amazon ECR (substitua <ACCOUNT_ID> pelo ID da sua conta AWS):
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# 2. Build e Push da imagem do Backend/Worker:
docker build -t sqlarena-backend:latest -f app/Dockerfile .
docker tag sqlarena-backend:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/sqlarena-backend:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/sqlarena-backend:latest

# 3. Build e Push da imagem do Frontend:
docker build -t sqlarena-frontend:latest -f frontend/Dockerfile ./frontend
docker tag sqlarena-frontend:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/sqlarena-frontend:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/sqlarena-frontend:latest
```
*(Em [`k8s/07-web-pod.yaml`](k8s/07-web-pod.yaml) e [`k8s/08-worker-pod.yaml`](k8s/08-worker-pod.yaml), atualize o campo `image:` com a URL do seu ECR caso esteja rodando no EKS em múltiplas máquinas. Em clusters locais ou K3s/Minikube em EC2, a imagem local `sqlarena-backend:latest` e `sqlarena-frontend:latest` com `imagePullPolicy: IfNotPresent` já funciona direto!).*

---

# ☸️ GUIA 3: IMPLANTAÇÃO NO KUBERNETES (Deployments, Services NodePort/ClusterIP, Secrets e HPA)

Todos os manifestos Kubernetes estão na pasta [`k8s/`](k8s/) numerados em ordem lógica de inicialização:

### 1. Configurar Credenciais de Forma Segura no Secret (`k8s/02-secrets.yaml`)
O arquivo [`k8s/02-secrets.yaml`](k8s/02-secrets.yaml) armazena de forma segura e isolada todas as senhas do banco, chaves JWT, credenciais do MinIO e credenciais da AWS para o DynamoDB:
* Abra `k8s/02-secrets.yaml` e preencha `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` e `AWS_SESSION_TOKEN` (ou crie/atualize via linha de comando sem salvar senhas em arquivo):
  ```powershell
  kubectl apply -f k8s/01-configmap.yaml
  kubectl apply -f k8s/02-secrets.yaml
  ```

### 2. Subir os Serviços de Dados e Mensageria (`ClusterIP` e `NodePort`)
```powershell
kubectl apply -f k8s/03-postgres-main.yaml
kubectl apply -f k8s/04-redis.yaml
kubectl apply -f k8s/05-minio.yaml
kubectl apply -f k8s/06-kafka.yaml
```

### 3. Subir os Pods Multi-Container da Aplicação (`sqlarena-web` e `sqlarena-worker`) e o Auto Scaling (`HPA`)
```powershell
kubectl apply -f k8s/07-web-pod.yaml
kubectl apply -f k8s/08-worker-pod.yaml
kubectl apply -f k8s/09-hpa.yaml
```
*(Ou aplique toda a pasta de uma só vez com: **`kubectl apply -f k8s/`**)*

### 4. Verificar Pods, Services (`NodePort` e `ClusterIP`) e Escalabilidade (`HPA`)
```powershell
# Verificar os Pods rodando (note a coluna READY 2/2 nos Pods Web e Worker!):
kubectl get pods

# Verificar os Services ClusterIP e NodePort:
kubectl get services

# Verificar o HorizontalPodAutoscaler (HPA):
kubectl get hpa
```

### Resumo dos Services Kubernetes Configurados

| Nome do Service | Tipo | Porta Interna | NodePort Externo | Função |
| :--- | :---: | :---: | :---: | :--- |
| **`sqlarena-web-nodeport`** | `NodePort` | `80` / `8000` | **`30080`** / **`30800`** | Acesso público externo ao Pod Web (Frontend React + API FastAPI) |
| **`sqlarena-web-clusterip`** | `ClusterIP` | `80` / `8000` | — | Comunicação interna no cluster (recebe os callbacks HTTP dos Pods de Worker) |
| **`postgres-service`** | `ClusterIP` | `5432` | — | Acesso interno do Backend ao PostgreSQL Principal (ex-RDS) |
| **`redis-service`** | `ClusterIP` | `6379` | — | Acesso interno do Backend ao Redis (Rate Limit e Cache) |
| **`minio-service`** | `ClusterIP` | `9000` / `9001` | — | Acesso interno S3 da API e dos Workers ao MinIO |
| **`minio-console-nodeport`** | `NodePort` | `9001` | **`30901`** | Acesso externo ao Console Web do MinIO no navegador |
| **`kafka-service`** | `ClusterIP` | `9092` | — | Broker Apache Kafka interno para envio e consumo de submissões |
| **`sqlarena-worker-clusterip`**| `ClusterIP` | `5432` | — | Descoberta interna dos Pods de Worker + Postgres Sandbox |

### Como Acessar a Aplicação no Kubernetes:
1. Descubra o IP externo de qualquer nó do cluster Kubernetes:
   ```powershell
   kubectl get nodes -o wide
   ```
2. Acesse no navegador usando as portas **NodePort**:
   * 🚀 **Plataforma Web SQLArena:** `http://<IP_PUBLICO_DO_NODE>:30080`
   * 📖 **Swagger UI (FastAPI):** `http://<IP_PUBLICO_DO_NODE>:30800/docs`
   * 🪣 **Console Web do MinIO:** `http://<IP_PUBLICO_DO_NODE>:30901`

---

## 🔑 Credenciais Prontas para Teste na Plataforma

| Perfil | Email | Senha | Funcionalidades Liberadas |
| :--- | :--- | :--- | :--- |
| **Aluno** | `gustavo@sqlarena.com` | `123456` | Dashboard de Questões, Arena SQL Monaco Editor, Fila ao Vivo, Histórico em Modal, Ranking e Perfil com Avatar |
| **Instrutor** | `admin@sqlarena.com` | `123456` | Painel de Criação/Publicação/Exclusão de Questões com Validação Sandbox, Logs do DynamoDB, Auditoria de CRUD e Gestão de Usuários |

---

## 🛑 Como Destruir a Infraestrutura na AWS (Custo Zero)

Para encerrar todos os recursos provisionados na AWS ao final dos testes:

```powershell
cd terraform

# Se subiu o Modo 2 (EC2 + Docker Compose):
terraform destroy -var-file="envs/modo2-ec2-compose.tfvars" -var-file="envs/credentials.tfvars" -auto-approve

# Se subiu o Modo 1 (EKS + DynamoDB):
terraform destroy -var-file="envs/modo1-eks.tfvars" -var-file="envs/credentials.tfvars" -auto-approve
```
