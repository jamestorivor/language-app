from pathlib import Path

BACKEND_PATH = Path(__file__).parent

PARENT_REPO_PATH = BACKEND_PATH.parent

DATA_PATH = PARENT_REPO_PATH / "data"

APP_PATH = BACKEND_PATH / "app"

DB_PATH = APP_PATH / "db"


