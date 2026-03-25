from fastapi import APIRouter
from app.api.endpoints import hello, auth, tasks

api_router = APIRouter()

api_router.include_router(
    hello.router,
    prefix="/hello",
    tags=["hello"],
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"],
)

api_router.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["tasks"],
)
