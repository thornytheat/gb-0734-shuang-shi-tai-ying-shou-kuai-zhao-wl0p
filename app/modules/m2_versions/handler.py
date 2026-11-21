from fastapi import APIRouter, Depends

from app.clock import CutQuery
from app.modules.m1_intake.service import load
from app.modules.m2_versions.service import versions_at
from app.store import Store, get_store

router = APIRouter(prefix="/api/versions", tags=["有效版本"])


@router.get("")
def versions(source_id: str, cut: CutQuery, store: Store = Depends(get_store)):
    return versions_at(load(store, source_id), cut)
