from fastapi import APIRouter, Depends

from app.clock import ArchiveRequest
from app.modules.m7_archive import repository, service
from app.modules.m7_archive.export import export_evidence
from app.store import Store, get_store

router = APIRouter(prefix="/api/archive", tags=["快照归档"])


@router.get("")
def history(source_id: str | None = None, store: Store = Depends(get_store)):
    with store.connect() as connection:
        return {"runs": repository.history(connection, source_id)}


@router.post("")
def archive(request: ArchiveRequest, store: Store = Depends(get_store)):
    return service.save(store, request.source_id, request.period())


@router.post("/{run_id}/rerun")
def rerun(run_id: str, store: Store = Depends(get_store)):
    return service.rerun(store, run_id)


@router.get("/{run_id}/export")
def export(run_id: str, store: Store = Depends(get_store)):
    return export_evidence(store, run_id)
