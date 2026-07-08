"""AzureRedOps API wrapper - FastAPI entry point with real CLI subprocess runner."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import activities, auth, tokens, phish, spray, sessions, oauth, mailbox
from app.utils import token_store
from app.config import TEST_MODE

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("azure-redops-api")


def create_app() -> FastAPI:
    token_store.init()
    app = FastAPI(title="AzureRedOps API Wrapper", version="3.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(?:localhost|127\.0\.0\.1)(?::\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for r in (activities, auth, tokens, phish, spray, sessions, oauth, mailbox):
        app.include_router(r.router)

    @app.get("/")
    def root():
        return {
            "ok": True,
            "service": "AzureRedOps",
            "version": "3.0",
            "test_mode": TEST_MODE,
        }

    @app.on_event("startup")
    def startup():
        if TEST_MODE:
            log.warning("AzureRedOps.py NOT found - running in TEST/MOCK mode")
        else:
            log.info("AzureRedOps.py located - real subprocess execution enabled")

    return app


app = create_app()