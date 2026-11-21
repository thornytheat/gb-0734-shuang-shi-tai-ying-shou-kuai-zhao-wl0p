from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import APP_DIR, SAMPLE, database_path
from app.errors import Problem, problem_response
from app.modules.m1_intake.handler import router as intake
from app.modules.m1_intake.service import ingest
from app.modules.m2_versions.handler import router as versions
from app.modules.m3_snapshot.handler import router as snapshot
from app.modules.m4_aging.handler import router as aging
from app.modules.m5_backfill.handler import router as backfill
from app.modules.m6_bridge.handler import router as bridge
from app.modules.m7_archive.handler import router as archive
from app.store import Store
from app.web import router as web


def create_app(path: Path | None = None):
    @asynccontextmanager
    async def lifespan(application):
        application.state.store = Store(path if path is not None else database_path())
        ingest(application.state.store, SAMPLE.read_bytes())
        yield

    application = FastAPI(title="双时态应收快照", lifespan=lifespan)
    application.add_exception_handler(Problem, problem_response)
    for router in (intake, versions, snapshot, aging, backfill, bridge, archive, web):
        application.include_router(router)
    application.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
    return application


app = create_app()
