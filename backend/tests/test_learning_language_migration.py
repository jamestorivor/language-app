import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_existing_users_default_to_japanese_and_downgrade_preserves_preferences():
    path = Path(__file__).resolve().parents[1] / "alembic/versions/ab73d5e80120_learning_language.py"
    spec = importlib.util.spec_from_file_location("learning_language_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO users (id) VALUES (1)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert connection.execute(text("SELECT learning_language FROM users")).scalar_one() == "ja"
            connection.execute(text("UPDATE users SET learning_language = 'en'"))
            with pytest.raises(RuntimeError, match="preferences exist"):
                migration.downgrade()
            assert connection.execute(text("SELECT learning_language FROM users")).scalar_one() == "en"
            connection.execute(text("UPDATE users SET learning_language = 'ja'"))
            migration.downgrade()
            assert "learning_language" not in {column["name"] for column in inspect(connection).get_columns("users")}


def test_onboarding_migration_preserves_existing_preferences_and_marks_new_accounts():
    path = Path(__file__).resolve().parents[1] / "alembic/versions/b4d9f2a7c103_learning_language_onboarding.py"
    spec = importlib.util.spec_from_file_location("onboarding_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, learning_language VARCHAR(2) NOT NULL)"))
        connection.execute(text("INSERT INTO users VALUES (1, 'en'), (2, 'ja')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert connection.execute(text("SELECT learning_language, learning_language_selected FROM users ORDER BY id")).all() == [("en", 1), ("ja", 1)]
            connection.execute(text("INSERT INTO users (id, learning_language) VALUES (3, 'ja')"))
            assert connection.execute(text("SELECT learning_language_selected FROM users WHERE id = 3")).scalar_one() is None
            migration.downgrade()
            assert "learning_language_selected" not in {column["name"] for column in inspect(connection).get_columns("users")}
