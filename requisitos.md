# Documento de Requisitos e Arquitetura do Sistema de Ensino de SQL

## 1. Objetivo e Visão Geral
O sistema tem como objetivo fornecer uma plataforma elástica e isolada para o ensino e prática de comandos SQL. Ele permite que professores cadastrem exercícios práticos e que alunos submetam consultas SQL como resposta. A execução das consultas ocorre em um ambiente de banco de dados real (PostgreSQL), garantindo feedback fidedigno baseado no comportamento exato de um SGBD. A arquitetura utiliza padrões de microsserviços e processamento assíncrono para garantir escalabilidade sob demanda, atendendo a requisitos acadêmicos estritos de elasticidade.

## 2. Arquitetura da Solução e Componentes
A arquitetura é dividida em duas camadas principais de processamento (API e Workers), desacopladas por mensageria, utilizando os seguintes serviços AWS:

* **Application Load Balancer (ALB):** Ponto de entrada público da aplicação. Distribui o tráfego HTTP/HTTPS entre as instâncias da API.
* **FastAPI:** API principal (Backend). Responsável por autenticação, rate limit, validação de regras de negócio, CRUD de questões e envio de mensagens para a fila. Não executa as consultas dos alunos.
* **Amazon SQS:** Fila de mensageria assíncrona que absorve os picos de tráfego e envia as submissões dos alunos para a camada de processamento.
* **Amazon EC2 (Workers + PostgreSQL):** Instâncias de processamento pesado em background. Cada máquina hospeda um script Worker e um SGBD PostgreSQL local, processando uma submissão por vez.
* **PostgreSQL (AWS RDS):** Banco relacional central para metadados da aplicação (usuários, questões, pontuações).
* **Amazon S3:** Armazenamento dos arquivos SQL (`schema.sql`, `data.sql`, `answer.sql`).
* **Redis/ElastiCache:** Armazenamento em cache de chaves de acesso rápido e do *Hash da Resposta Esperada*.
* **Amazon DynamoDB:** Log imutável (NoSQL) contendo o histórico detalhado de todas as execuções, erros e resultados.

## 3. Elasticidade e Auto Scaling (Topologia de Duplo ASG)
Para atender rigorosamente aos requisitos de provisionamento elástico da aplicação (baseado em CPU) e, ao mesmo tempo, manter as melhores práticas de processamento em background, o sistema utilizará dois Auto Scaling Groups (ASGs) distintos:

### 3.1. ASG 1: Camada Web (API FastAPI)
Este grupo gerencia a aplicação exposta à internet e atende diretamente às regras de balanceamento de carga exigidas.
* **Configuração de Instância:** Família `t2.micro` ou `t3.small`.
* **Rede:** Protegido e roteado pelo **Application Load Balancer (ALB)** via *Round Robin*.
* **Regras de Elasticidade (Target Tracking via CloudWatch):**
  * **Scale Out:** Se a média de `CPUUtilization` do grupo exceder **70% por mais de 1 minuto**, uma nova instância será criada (até o máximo de 3).
  * **Scale In:** Se a média de `CPUUtilization` cair abaixo de **25% por mais de 1 minuto**, uma instância será finalizada.
  * **Limites:** Mínimo de 1 e Máximo de 3 instâncias.

### 3.2. ASG 2: Camada de Processamento (Workers)
Este grupo gerencia a execução assíncrona das queries, não recebe tráfego HTTP e puxa tarefas da SQS.
* **Configuração de Instância:** Família `t2.micro` ou `t3.small` contendo o Worker e o PostgreSQL.
* **Rede:** Sem Load Balancer associado (*Pull-based* via SQS).
* **Regras de Elasticidade:** O gatilho de escala utiliza a métrica `ApproximateNumberOfMessagesVisible` da fila SQS. O grupo cresce quando há acúmulo de submissões pendentes e encolhe quando a fila permanece ociosa.
* **Limites:** Mínimo de 1 e Máximo de 3 instâncias.

## 4. Estrutura e Ciclo de Vida das Questões
As questões são **imutáveis**. Não há versionamento de conteúdo para simplificar o rastreamento e a engenharia de dados.

* **DRAFT:** Estado inicial. A questão não é visível para alunos e não aceita submissões.
* **READY:** A questão foi validada tecnicamente (arquivos SQL rodaram com sucesso e o Hash foi gerado). Continua invisível aos alunos. Uma questão em `READY` **não pode ser editada**, apenas deletada e recriada.
* **PUBLISHED:** A questão foi ao ar. Está visível para os alunos, e os Workers já possuem os metadados para processá-la. Não pode retornar para `READY` ou `DRAFT`.
* **Deleção:** Permitida a qualquer momento. O ID (sequencial) nunca é reutilizado. Remove-se a questão do RDS, os arquivos do S3, e uma mensagem de controle (`DELETE_QUESTION`) é enviada via fila para que todos os Workers apaguem os respectivos schemas locais. O histórico de tentativas no DynamoDB é preservado.

## 5. Arquivos SQL e Validação
Uma questão baseia-se em três arquivos providenciados pelo professor (armazenados no S3):
1. `schema.sql`: Estrutura do banco (`CREATE TABLE`, `CREATE INDEX`).
2. `data.sql`: Carga de dados inicial (`INSERT INTO`).
3. `answer.sql`: A consulta que gera o resultado correto.

* **Obrigatoriedade do ORDER BY:** Na transição de `DRAFT` para `READY`, a API verifica sintaticamente se o professor incluiu `ORDER BY` no `answer.sql`. Se ausente, o cadastro falha. O aluno, por outro lado, **não** é obrigado a usar `ORDER BY`, desde que seu resultado saia na mesma ordem exigida pela questão.

## 6. Motor de Execução Local (PostgreSQL nas EC2s)
As instâncias da Camada de Processamento reconstroem as questões publicadas no PostgreSQL local durante a sua inicialização (via *bootstrapping* baixando dados do S3).

* **Isolamento:** Cada questão reside em um schema isolado (ex: `pergunta_10`). O Worker utiliza `SET search_path TO pergunta_10` para esconder a arquitetura interna do aluno.
* **Segurança e Permissões:** O script do aluno roda sob uma role de banco limitada a leitura (`SELECT`). DDL e DML de escrita são nativamente bloqueados pelo SGBD.
* **Single-Thread Worker:** O Worker consome 1 mensagem da SQS, executa no banco, apaga da fila e pega a próxima. Essa execução estritamente sequencial evita colisões de concorrência e race conditions (ex: exclusão de schema conflitando com query em andamento).
* **Timeout:** Para evitar *Cross Joins* e queries maliciosas que comprometam a CPU e a fila, o Worker aplica `SET statement_timeout` na sessão do aluno.

## 7. Comparação Rigorosa e Hashes de Resposta
Para garantir alta performance de rede e economia de memória (evitando trafegar resultados gigantes em plain text):

* **Estratégia de SHA-256:** O `answer.sql` do professor gera um resultado que é serializado canonicamente no Backend e convertido em um Hash (armazenado no Redis). A query do aluno passará pelo mesmo processo no Worker local. A validação é uma comparação de Hashes.
* **Strict Mode (Regra de 100%):** O resultado do aluno deve ser perfeitamente igual em valores, colunas, ordem, nulos e duplicatas. Não existe tolerância matemática (ex: `FLOAT` não é igual a `NUMERIC`, `10.5` não é igual a `10.50`). Se os hashes divergirem, a resposta é incorreta. O sistema não proverá feedback de UX para dicas de tipo de dado.

## 8. Submissões e Sistema de Pontuação
* **Rate Limit:** Intervalo global de **5 segundos** por aluno entre qualquer tentativa, garantido pela FastAPI/Redis.
* **Pontuação:** Resposta correta (Hashes conferem) gera +1 ponto (salvo no RDS). Tentativas erradas ou repetidas da mesma questão não acumulam pontos.
* **Registro Imutável:** Todas as execuções, acertadas ou não, e os respectivos logs nativos de erro do PostgreSQL (para feedback técnico do aluno), são salvas no AWS DynamoDB.

## 9. Fluxo Transacional Completo (Aluno)
1. O aluno envia o comando `SELECT` através da interface.
2. A requisição é roteada pelo **Application Load Balancer** para uma das instâncias EC2 da **Camada Web (ASG 1)**.
3. A **FastAPI** valida o token JWT e o Rate Limit.
4. A API publica o payload na SQS e devolve `HTTP 202 Accepted` para o frontend.
5. Um Worker ocioso da **Camada de Processamento (ASG 2)** puxa a mensagem da SQS.
6. O Worker aplica o timeout, define o schema local da questão e executa a query em *Read-Only*.
7. O Worker gera o Hash do resultado e consulta o Redis para bater com o gabarito.
8. Em caso de acerto inédito, o Worker consolida o ponto no RDS.
9. O log da tentativa, incluindo tempo e resultado/erro, é consolidado no DynamoDB.
10. O Worker apaga a mensagem da SQS e o ciclo finaliza. (Frontend obtém o status via Polling).