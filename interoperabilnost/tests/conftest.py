"""Pytest fixtures - privremena SQLite baza."""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB = Path("/tmp/interoperabilnost_pytest.db")


@pytest.fixture(scope="session")
def client():
    if TEST_DB.exists():
        TEST_DB.unlink()
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB}"
    os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-characters-long"
    os.environ["WEBHOOK_SECRET"] = "whsec-test"
    os.environ["RABBITMQ_URL"] = ""

    from app.main import app

    with TestClient(app) as c:
        yield c

    if TEST_DB.exists():
        TEST_DB.unlink()
