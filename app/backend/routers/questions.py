"""
Rotas de exercícios (questões), no formato que app/frontend/src/services/questionService.js
já espera consumir. Metadados (título, dificuldade, status) ainda ficam em memória
(ver store.py) até o RDS existir -- mas S3 e DynamoDB já estão 100%
reais aqui..
"""
import logging

from fastapi import APIRouter, Depends, Form, HTTPException

from app.backend import store
from app.backend.dependencies import get_dynamo_manager, get_s3_manager
from app.dynamodb.dynamo_manager import DynamoDBManager
from app.s3.s3_manager import S3Manager

logger = logging.getLogger(__name__)
router = APIRouter()

# TODO(CSV): o upload de dataset.csv (arquivo binário do Requisito 3) está
# temporariamente fora, pendente de confirmação com o professor sobre se o
# conjunto de arquivos .sql já atende ao requisito. Se a resposta for "não,
# precisa de binário", restaurar S3Manager.upload_question_dataset_csv (já
# implementado e testado antes) e o parâmetro dataset_csv abaixo.


def _notify_worker_question_deleted(question_id: int) -> None:
    """Publica um evento DELETE_QUESTION no SQS (ver docs/s3.md secao 5)."""
    try:
        from app.sqs.queue_manager import SQSQueueManager

        sqs = SQSQueueManager()
        sqs.send_message(
            payload={"event_type": "DELETE_QUESTION", "question_id": question_id},
            attributes={"event_type": "DELETE_QUESTION"},
        )
    except Exception as e:
        logger.warning(f"Não foi possível notificar o SQS sobre a deleção da questão {question_id}: {e}")


@router.get("")
def list_questions():
    return store.list_all()


@router.get("/{question_id}")
def get_question(question_id: int):
    question = store.get(question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Questão não encontrada")
    return question


@router.post("", status_code=201)
def create_question(
    title: str = Form(...),
    difficulty: str = Form("Médio"),
    category: str = Form("Geral"),
    schema_sql: str = Form(...),
    data_sql: str = Form(...),
    answer_sql: str = Form(...),
    user_id: str = Form("sistema"),
    s3: S3Manager = Depends(get_s3_manager),
    dynamo: DynamoDBManager = Depends(get_dynamo_manager),
):
    # Mesma validação que já existia no mock do frontend (Requisito do gabarito
    # determinístico): o answer.sql precisa ter ORDER BY.
    if "ORDER BY" not in answer_sql.upper():
        raise HTTPException(
            status_code=422,
            detail="O answer_sql deve conter cláusula ORDER BY para garantir determinismo.",
        )

    # TODO(RDS): troque por um INSERT real e pegue o id gerado pelo Postgres.
    question = store.create(
        {
            "title": title,
            "difficulty": difficulty,
            "category": category,
            "status": "DRAFT",
        }
    )
    question_id = question["id"]

    s3.ensure_bucket_exists()
    s3.upload_question_sql_files(question_id, schema_sql, data_sql, answer_sql)

    dynamo.ensure_crud_table_exists()
    dynamo.log_crud_action(
        action_type="CREATE_EXERCISE",
        entity="exercise",
        entity_id=question_id,
        user_id=user_id,
        changed_data={"title": title, "difficulty": difficulty, "category": category},
    )

    return question


@router.post("/{question_id}/publish")
def publish_question(
    question_id: int,
    user_id: str = "sistema",  # query param -- o frontend hoje não manda corpo nesse POST
    dynamo: DynamoDBManager = Depends(get_dynamo_manager),
):
    # TODO(RDS): troque por um UPDATE real.
    question = store.update(question_id, status="PUBLISHED")
    if question is None:
        raise HTTPException(status_code=404, detail="Questão não encontrada")

    dynamo.log_crud_action(
        action_type="PUBLISH_EXERCISE",
        entity="exercise",
        entity_id=question_id,
        user_id=user_id,
        changed_data={"status": "PUBLISHED"},
    )
    return question


@router.delete("/{question_id}")
def delete_question(
    question_id: int,
    user_id: str = "sistema",  # query param -- o frontend hoje não manda corpo no DELETE
    s3: S3Manager = Depends(get_s3_manager),
    dynamo: DynamoDBManager = Depends(get_dynamo_manager),
):
    # TODO(RDS): troque por um DELETE real.
    existed = store.delete(question_id)
    if not existed:
        raise HTTPException(status_code=404, detail="Questão não encontrada")

    s3.delete_question_files(question_id)
    _notify_worker_question_deleted(question_id)

    dynamo.log_crud_action(
        action_type="DELETE_EXERCISE",
        entity="exercise",
        entity_id=question_id,
        user_id=user_id,
    )
    return {"deleted": True, "id": question_id}