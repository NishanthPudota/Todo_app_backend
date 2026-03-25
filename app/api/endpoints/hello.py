from fastapi import APIRouter

router= APIRouter()

@router.get("/hello", response_model=str)
def hello():
    return "Hello Hi, from Todo backend API!"



