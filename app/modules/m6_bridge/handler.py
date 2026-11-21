from fastapi import APIRouter, Depends

from app.clock import PeriodQuery
from app.modules.m1_intake.service import load
from app.modules.m6_bridge.service import period_book
from app.store import Store, get_store

router = APIRouter(prefix="/api/bridge", tags=["期间桥接"])


@router.get("")
def bridge(source_id: str, period: PeriodQuery, store: Store = Depends(get_store)):
    return period_book(load(store, source_id), period)["bridge"]
