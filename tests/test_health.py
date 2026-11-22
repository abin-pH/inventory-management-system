
import importlib.util
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# CI-only values; no connection to the database is made.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "ci-test-secret-not-for-production"

ROOT = Path(__file__).resolve().parents[1]


def load_service(name):
    path = ROOT / "services" / name / "main.py"
    spec = importlib.util.spec_from_file_location(
        f"test_{name}_service", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("service", ["auth", "products", "stock"])
def test_health(service):
    module = load_service(service)

    # No lifespan startup: no database table creation.
    client = TestClient(module.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

