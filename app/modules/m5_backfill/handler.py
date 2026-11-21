from fastapi import APIRouter, Depends

from app.clock import PeriodQuery
from app.modules.m1_intake.service import load
from app.modules.m5_backfill.service import compare_opening
from app.store import Store, get_store

router = APIRouter(prefix="/api/backfill", tags=["迟报回补"])


@router.get("")
def backfill(source_id: str, period: PeriodQuery, store: Store = Depends(get_store)):
    return compare_opening(load(store, source_id), period)[2]
