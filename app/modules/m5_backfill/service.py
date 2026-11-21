from app.clock import Cut
from app.modules.m3_snapshot.service import ACCOUNT, snapshot
from app.modules.m5_backfill.changes import changed_events, invoice_adjustments


def compare_opening(data, period):
    before = snapshot(data, period.opening)
    restated = snapshot(data, Cut(period.opening.effective, period.closing.known))
    return before, restated, {
        "before_cut": before["cut"], "after_cut": restated["cut"],
        "totals": {key: restated["totals"][key] - before["totals"][key] for key in ACCOUNT},
        "invoices": invoice_adjustments(before, restated), "changes": changed_events(before, restated),
    }
