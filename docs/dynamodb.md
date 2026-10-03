
## 1. Log de ações de CRUD (DynamoDB)

### O que existe
Arquivo: `app/dynamodb/dynamo_manager.py`, classe `DynamoDBManager`.

Além da tabela de submissões que já existia (`sqlarena-submissions-log`), agora há uma
**segunda tabela**, separada, só para auditoria de ações de CRUD:

- **Tabela:** `sqlarena-crud-actions-log`
- **Chave primária:** `action_id` (string, gerado automaticamente)
- **GSI `EntityIndex`:** `entity_id` (hash) + `created_at` (range) — permite consultar todo
  o histórico de uma entidade específica (ex: um exercício), em ordem cronológica.

### Métodos disponíveis

```python
from app.dynamodb.dynamo_manager import DynamoDBManager

manager = DynamoDBManager()
manager.ensure_crud_table_exists()  # idempotente, cria se não existir

# Registrar uma ação
manager.log_crud_action(
    action_type="CREATE_EXERCISE",   # ou UPDATE_EXERCISE, DELETE_EXERCISE, SUBMIT_ANSWER, etc.
    entity="exercise",
    entity_id="exercise_456",
    user_id="professor-7",
    changed_data={"title": "Consultas do dia"},  # opcional
)

# Consultar o histórico de uma entidade
historico = manager.get_entity_history("exercise_456")

# Listar as ações mais recentes (painel admin)
manager.list_crud_actions(limit=50)
```

### Quem deve usar isso
**Quem escrever os endpoints de criar/editar/deletar exercício** (API/backend) precisa
chamar `log_crud_action(...)` dentro de cada endpoint, logo após a operação ser concluída
com sucesso. `action_type` fica livre — sugestão: `CREATE_EXERCISE`, `UPDATE_EXERCISE`,
`DELETE_EXERCISE`, `SUBMIT_ANSWER`.

### Terraform
`terraform/dynamodb.tf` já cria essa tabela junto com a de submissões
(`terraform apply -var-file="envs/local.tfvars"` recria as duas).

### Como foi validado
Rodado contra o Ministack local (`app/testes/main_dynamodb.py`, passos 8-10) e também
simulado com a lib `moto` (mock real de DynamoDB) antes de ir pro ambiente local — criação
de tabela, 4 ações registradas (CREATE/UPDATE/DELETE/SUBMIT) e consulta via GSI retornando
na ordem correta.

---

## 2. Perguntas que o time pode receber

**"Onde fica o log de auditoria?"**
DynamoDB, tabela `sqlarena-crud-actions-log`. Separada da tabela de submissões porque os
padrões de consulta são diferentes (uma é por entidade, outra por aluno).

**"Isso já está na AWS de verdade ou só local?"**
Só validado no Ministack (ambiente local) até agora. O Terraform (`s3.tf`, `dynamodb.tf`)
já está pronto para aplicar na AWS Academy quando o time decidir fazer o deploy real —
basta trocar `-var-file="envs/local.tfvars"` por `-var-file="envs/aws.tfvars"`.

## 3. Onde está o código

| Gerenciador DynamoDB (submissões + CRUD) | `app/dynamodb/dynamo_manager.py` |
| Teste/demo DynamoDB | `app/testes/main_dynamodb.py` |
| Infraestrutura DynamoDB | `terraform/dynamodb.tf` |