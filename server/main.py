"""li-toolkit — local API server for LinkedIn post analytics."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routes import router as api_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize the database on startup."""
    init_db()
    yield


app = FastAPI(
    title="li-toolkit",
    version="0.1.0",
    description=(
        "Local API server that stores your LinkedIn"
        " posts and computes analytics."
    ),
    lifespan=lifespan,
)

# CORS — open to all origins so the Chrome extension can reach the server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("LI_TOOLKIT_HOST", "127.0.0.1")
    port = int(os.environ.get("LI_TOOLKIT_PORT", "9247"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
