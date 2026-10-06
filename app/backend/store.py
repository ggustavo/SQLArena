"""
TODO(RDS): este módulo é um placeholder em memória para os metadados de questão
(título, dificuldade, categoria, status). Quando integrar o RDS, as
funções deste arquivo devem ser substituídas por queries reais ao Postgres —
os routers já foram escritos para chamar só estas funções, então a troca deve
ficar isolada aqui, sem precisar mexer em app/backend/routers/*.

Isso existe só para o backend conseguir rodar de ponta a ponta (S3 + DynamoDB)
antes do RDS estar pronto, e para o frontend ter uma API real pra conversar
em vez de ficar só no modo mock.
"""
from itertools import count
from typing import Any, Dict, List, Optional

_questions: Dict[int, Dict[str, Any]] = {}
_id_counter = count(1)


def create(data: Dict[str, Any]) -> Dict[str, Any]:
    question_id = next(_id_counter)
    question = {"id": question_id, **data}
    _questions[question_id] = question
    return question


def get(question_id: int) -> Optional[Dict[str, Any]]:
    return _questions.get(question_id)


def list_all() -> List[Dict[str, Any]]:
    return list(_questions.values())


def update(question_id: int, **fields: Any) -> Optional[Dict[str, Any]]:
    question = _questions.get(question_id)
    if question is None:
        return None
    question.update(fields)
    return question


def delete(question_id: int) -> bool:
    return _questions.pop(question_id, None) is not None
