"""FastAPI application entry point.

Run:  uvicorn app.main:app --reload
Docs: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (registers the tables with SQLAlchemy)
from .config import CORS_ORIGINS
from .constants import DISCLAIMER
from .database import Base, SessionLocal, engine
from .domain.state import state
from .errors import register_error_handlers
from .routes import admin, analytics, dispatches, dsa_lab, inventory, requests
from .seed import seed_if_empty


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)           # create tables on first run
    with SessionLocal() as db:
        seed_if_empty(db)                           # demo data on a brand-new database
        state.rebuild(db)                           # heaps + hash indexes rebuilt from the database
    yield


app = FastAPI(
    title="Smart Emergency Blood Allocation & Dispatch Engine",
    description="Prioritize urgent requests. Allocate compatible stock. Reduce expiry waste.\n\n" + DISCLAIMER,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)

for module in (inventory, requests, dispatches, analytics, dsa_lab, admin):
    app.include_router(module.router)


@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "ok", "disclaimer": DISCLAIMER}
