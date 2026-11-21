from fastapi import Response

from app.errors import Problem
from app.evidence import canonical, digest
from app.modules.m7_archive.service import read_run


def export_evidence(store, run_id):
    stored = read_run(store, run_id)
    if digest(canonical(stored["result"])) != stored["manifest"]["result_digest"]:
        raise Problem("ARCHIVE_MISMATCH", "归档证据摘要不符", 409)
    return Response(canonical(stored), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="receivable-{run_id[:12]}.json"'})
