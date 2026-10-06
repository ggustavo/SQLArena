"""
Ponto de entrada da API do SQLArena.

Esqueleto mínimo do backend: expõe as rotas que o frontend (frontend/src/services/*)
já espera consumir em http://localhost:8000/api/*. Rodar com:

    uvicorn app.backend.main:app --reload --port 8000

(a partir da raiz do repositório, com o venv ativado e o Ministack no ar)

Partes que dependem do RDS usam um armazenamento em memória como
placeholder -- ver app/backend/store.py e os comentários TODO(RDS).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.backend.routers import audit, questions

app = FastAPI(title="SQLArena API", version="0.1.0")

# Libera o frontend Vite (porta padrão 5173) a chamar a API durante o desenvolvimento.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(questions.router, prefix="/api/questions", tags=["questions"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
