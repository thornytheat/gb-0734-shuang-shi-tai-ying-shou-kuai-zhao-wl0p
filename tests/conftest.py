import csv
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.clock import period_query
from app.config import SAMPLE
from app.main import create_app
from app.modules.m1_intake.contract import COLUMNS
from app.modules.m1_intake.reader import read


@pytest.fixture(scope="session")
def raw():
    return SAMPLE.read_bytes()


@pytest.fixture(scope="session")
def branch_raw():
    return (Path(SAMPLE).parent / "branch-gb18030.csv").read_bytes()


@pytest.fixture
def data(raw):
    return read(raw)


@pytest.fixture
def params():
    return {"open_effective": "2025-12-31", "open_known": "2025-12-31T23:59+08:00",
            "effective": "2026-01-31", "known": "2026-02-06T12:00+08:00"}


@pytest.fixture
def period(params):
    return period_query(**params)


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "archive.sqlite3")) as session:
        yield session


@pytest.fixture
def query(client, params):
    return {"source_id": client.get("/api/intake/sample").json()["source_id"], **params}


@pytest.fixture
def make_csv():
    def make(*rows, header=COLUMNS):
        dest = io.StringIO(newline="")
        writer = csv.writer(dest)
        writer.writerow(header)
        writer.writerows(rows)
        return dest.getvalue().encode()
    return make
