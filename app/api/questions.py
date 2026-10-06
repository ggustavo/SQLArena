from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models import Question, Category, User, UserSolvedQuestion
from app.api.deps import get_optional_current_user, require_instructor
from app.s3.s3_manager import S3Manager
from app.dynamodb.dynamo_manager import DynamoDBManager
from app.cache.redis_client import redis_client

router = APIRouter(prefix="/questions", tags=["Questões"])

s3_manager = S3Manager()
dynamo_manager = DynamoDBManager()

class QuestionCreateRequest(BaseModel):
    title: str
    difficulty: str = "Médio"
    categories: List[str] = []
    category: Optional[str] = None
    description: str = ""
    schemaSql: str = ""
    dataSql: str = ""
    answerSql: str = ""
    sampleTables: Optional[List[Dict[str, Any]]] = None
    expectedColumns: Optional[List[str]] = None

@router.get("")
def list_questions(
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Retorna as questões. Alunos só veem PUBLISHED; instrutores veem tudo.
    Enriquece com status (SOLVED, ATTEMPTED, UNSOLVED) baseado nas resoluções do usuário.
    """
    is_instructor = user and user.role == "INSTRUCTOR"
    
    query = db.query(Question)
    if not is_instructor:
        query = query.filter(Question.status == "PUBLISHED")
    
    questions = query.order_by(Question.id.asc()).all()

    # Mapeamento de resoluções do usuário
    solved_set = set()
    if user:
        solved_ids = db.query(UserSolvedQuestion.question_id).filter_by(user_id=user.id).all()
        solved_set = {sid[0] for sid in solved_ids}

    result = []
    for q in questions:
        cats = sorted([c.name for c in q.categories], key=lambda x: x.lower())
        if not cats:
            cats = ["Filtragem"]

        is_solved = q.id in solved_set
        q_status = "SOLVED" if is_solved else "UNSOLVED"

        result.append({
            "id": q.id,
            "title": q.title,
            "difficulty": q.difficulty,
            "categories": cats,
            "category": cats[0] if cats else "Filtragem",
            "status": q_status,
            "publishedStatus": q.status,
            "description": q.description or "",
            "schemaSql": q.schema_sql or "",
            "sampleTables": q.sample_tables or [],
            "expectedColumns": q.expected_columns or [],
        })
    return result

@router.get("/{question_id}")
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retorna detalhes de uma questão pelo ID."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Questão não encontrada.")
    
    is_instructor = user and user.role == "INSTRUCTOR"
    if q.status != "PUBLISHED" and not is_instructor:
        raise HTTPException(status_code=403, detail="Questão ainda não publicada.")

    cats = sorted([c.name for c in q.categories], key=lambda x: x.lower())
    if not cats:
        cats = ["Filtragem"]

    is_solved = False
    if user:
        is_solved = db.query(UserSolvedQuestion).filter_by(user_id=user.id, question_id=q.id).first() is not None

    return {
        "id": q.id,
        "title": q.title,
        "difficulty": q.difficulty,
        "categories": cats,
        "category": cats[0] if cats else "Filtragem",
        "status": "SOLVED" if is_solved else "UNSOLVED",
        "publishedStatus": q.status,
        "description": q.description or "",
        "schemaSql": q.schema_sql or "",
        "sampleTables": q.sample_tables or [],
        "expectedColumns": q.expected_columns or [],
    }

@router.post("", status_code=status.HTTP_201_CREATED)
def create_question(
    payload: QuestionCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor)
):
    """
    Cria uma nova questão (Instrutor).
    Valida a presença obrigatória de ORDER BY no gabarito (Requisito 5),
    salva os arquivos SQL no S3, persiste no RDS e grava auditoria no DynamoDB.
    """
    answer_upper = (payload.answerSql or "").upper()
    if "ORDER BY" not in answer_upper:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro de Validação (Requisito 5): A consulta gabarito (answer.sql) DEVE conter cláusula ORDER BY para garantir determinismo."
        )

    # Cria registro no RDS
    new_q = Question(
        title=payload.title,
        difficulty=payload.difficulty or "Médio",
        status="PUBLISHED",
        description=payload.description or "",
        schema_sql=payload.schemaSql or "",
        sample_tables=payload.sampleTables or [],
        expected_columns=payload.expectedColumns or [],
        created_by=user.id
    )

    # Associa categorias
    cat_names = payload.categories or ([payload.category] if payload.category else ["Filtragem"])
    for c_name in cat_names:
        c = db.query(Category).filter(Category.name == c_name).first()
        if c:
            new_q.categories.append(c)

    db.add(new_q)
    db.commit()
    db.refresh(new_q)

    # Upload dos scripts no S3
    try:
        s3_manager.upload_question_sql_files(
            question_id=new_q.id,
            schema_sql=payload.schemaSql or "-- Sem schema\n",
            data_sql=payload.dataSql or "-- Sem dados\n",
            answer_sql=payload.answerSql
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao salvar scripts SQL no Amazon S3: {e}"
        )

    # Auditoria no DynamoDB
    try:
        dynamo_manager.log_crud_action(
            action_type="CREATE_EXERCISE",
            entity_id=f"exercise_{new_q.id}",
            user_id=user.id,
            details={"title": new_q.title, "difficulty": new_q.difficulty}
        )
    except Exception:
        pass

    cats = sorted([c.name for c in new_q.categories], key=lambda x: x.lower())
    return {
        "id": new_q.id,
        "title": new_q.title,
        "difficulty": new_q.difficulty,
        "categories": cats,
        "category": cats[0] if cats else "Filtragem",
        "status": "UNSOLVED",
        "publishedStatus": new_q.status,
        "description": new_q.description,
        "schemaSql": new_q.schema_sql,
        "sampleTables": new_q.sample_tables,
        "expectedColumns": new_q.expected_columns
    }

@router.delete("/{question_id}", status_code=status.HTTP_200_OK)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor)
):
    """Exclui atomicamente uma questão do RDS, do S3 e grava log no DynamoDB."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Questão não encontrada.")

    # Remove do S3
    try:
        s3_manager.delete_question_files(question_id)
    except Exception:
        pass

    # Remove do RDS
    db.delete(q)
    db.commit()

    # Log no DynamoDB
    try:
        dynamo_manager.log_crud_action(
            action_type="DELETE_EXERCISE",
            entity_id=f"exercise_{question_id}",
            user_id=user.id,
            details={"action": "deleted", "question_id": question_id}
        )
    except Exception:
        pass

    return {"message": f"Questão #{question_id} removida com sucesso."}

@router.post("/{question_id}/publish", status_code=status.HTTP_200_OK)
def publish_question(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor)
):
    """Publica uma questão mudando o status para PUBLISHED."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Questão não encontrada.")
    q.status = "PUBLISHED"
    db.commit()
    db.refresh(q)

    try:
        dynamo_manager.log_crud_action(
            action_type="PUBLISH_EXERCISE",
            entity_id=f"exercise_{question_id}",
            user_id=user.id,
            details={"title": q.title, "status": "PUBLISHED"}
        )
    except Exception:
        pass

    return {
        "id": q.id,
        "title": q.title,
        "status": q.status,
        "publishedStatus": q.status,
        "message": f"Questão #{question_id} publicada com sucesso."
    }
