import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
SAMPLE = APP_DIR.parent / "sample_data" / "receivable.csv"
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 5000
RULE_VERSION = "ar-bitemporal-1"
DISPLAY_ZONE = "+08:00"


def database_path() -> Path:
    return Path(os.environ.get("RECEIVABLE_DB", "workbench.sqlite3"))
