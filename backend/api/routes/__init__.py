from fastapi import APIRouter
from api.routes.auth import router as auth_router
from api.routes.questions import router as questions_router
from api.routes.submissions import router as submissions_router
from api.routes.scores import router as scores_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(questions_router)
api_router.include_router(submissions_router)
api_router.include_router(scores_router)
