
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_async_db

class DummyDBSession:
    async def execute(self, *_args, **_kwargs):
        return None

async def override_db():
    yield DummyDBSession()

@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def override_db_dependency():
    app.dependency_overrides[get_async_db] = override_db
    yield












