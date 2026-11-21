from fastapi import APIRouter, Depends

from app.clock import CutQuery
from app.modules.m1_intake.service import load
from app.modules.m3_snapshot.service import snapshot
from app.modules.m4_aging.service import age
from app.store import Store, get_store

router = APIRouter(prefix="/api/aging", tags=["过期应收"])


@router.get("")
def aging(source_id: str, cut: CutQuery, store: Store = Depends(get_store)):
    return age(snapshot(load(store, source_id), cut))
