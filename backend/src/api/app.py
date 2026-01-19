from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import api_router


def create_app() -> FastAPI:
    app = FastAPI(title="Splendor 人机对战 API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
