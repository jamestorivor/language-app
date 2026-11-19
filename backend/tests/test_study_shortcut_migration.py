import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_shortcut_migration_preserves_saved_bindings():
    path = Path(__file__).resolve().parents[1] / "alembic/versions/d9e2c68a315f_study_shortcuts.py"
    spec = importlib.util.spec_from_file_location("shortcut_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO users (id) VALUES (1)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert "study_shortcuts" in {column["name"] for column in inspect(connection).get_columns("users")}
            connection.execute(text("UPDATE users SET study_shortcuts = :value"), {"value": '{"again":"q"}'})
            with pytest.raises(RuntimeError, match="custom study shortcuts"):
                migration.downgrade()
            assert connection.execute(text("SELECT study_shortcuts FROM users")).scalar_one() == '{"again":"q"}'
            connection.execute(text("UPDATE users SET study_shortcuts = NULL"))
            migration.downgrade()
            assert "study_shortcuts" not in {column["name"] for column in inspect(connection).get_columns("users")}
