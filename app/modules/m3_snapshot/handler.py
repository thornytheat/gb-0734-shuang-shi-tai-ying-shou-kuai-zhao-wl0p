from fastapi import APIRouter, Depends

from app.clock import CutQuery
from app.modules.m1_intake.service import load
from app.modules.m3_snapshot.service import snapshot
from app.store import Store, get_store

router = APIRouter(prefix="/api/snapshot", tags=["双时态截面"])


@router.get("")
def read_snapshot(source_id: str, cut: CutQuery, store: Store = Depends(get_store)):
    return snapshot(load(store, source_id), cut)
