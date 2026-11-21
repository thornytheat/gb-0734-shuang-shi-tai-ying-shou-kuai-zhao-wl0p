from fastapi import APIRouter, Depends, File, UploadFile

from app.config import MAX_BYTES, SAMPLE
from app.evidence import digest
from app.modules.m1_intake.service import ingest, load, summarize
from app.store import Store, get_store

router = APIRouter(prefix="/api/intake", tags=["变更收件"])


@router.get("/sample")
def sample(store: Store = Depends(get_store)):
    source_id = digest(SAMPLE.read_bytes())
    return summarize(source_id, load(store, source_id))


@router.post("")
def upload(file: UploadFile = File(...), store: Store = Depends(get_store)):
    return ingest(store, file.file.read(MAX_BYTES + 1))


@router.get("/{source_id}")
def source(source_id: str, store: Store = Depends(get_store)):
    return summarize(source_id, load(store, source_id))
