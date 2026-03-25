from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.telemetry import setup_telemetry
from app.database import engine
from app.api.router import api_router
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="A simple TODO backend API",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    def health_check():
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }

    # Bug 7 fixed: setup_telemetry() is called here — INSIDE create_app() —
    # so it runs exactly once regardless of uvicorn --reload re-imports.
    # Previously it was called at module level (after create_app()) which caused
    # FastAPIInstrumentor.instrument_app() to run multiple times on reload,
    # producing duplicate spans for every request.
    setup_telemetry(app, engine)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
