import os
from pathlib import Path


def sqlite_db_path() -> Path:
    """
    Возвращает путь к SQLite базе.

    Настраивается через переменную окружения SQLITE_DB_PATH.
    По умолчанию используется database.sqlite3 в папке проекта `tmp/`,
    чтобы на хостинге было проще обеспечить запись в каталог.
    """
    db_path = os.environ.get("SQLITE_DB_PATH", "").strip()
    if db_path:
        return Path(db_path).expanduser().resolve()

    project_dir = Path(__file__).resolve().parent
    default_path = (project_dir / "tmp" / "database.sqlite3").resolve()
    default_path.parent.mkdir(parents=True, exist_ok=True)
    return default_path


def secret_key() -> str:
    return os.environ.get("SECRET_KEY", "course-project-secret-key")


def port() -> int:
    return int(os.environ.get("PORT", "5000"))


def debug() -> bool:
    return os.environ.get("FLASK_DEBUG", "0").strip() == "1"


ACCESS_SCHEMA_VERSION = 1
