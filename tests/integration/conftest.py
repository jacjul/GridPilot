import asyncio
import os
import time

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.redis import r
from app.db.database import Base, engine


@pytest.fixture(scope="session", autouse=True)
def require_integration_mode():
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("Integration tests are disabled. Set RUN_INTEGRATION=1 to enable.")


@pytest.fixture(scope="session", autouse=True)
def require_dependencies_up(require_integration_mode):
    last_db_error = None
    for _ in range(20):
        try:
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            last_db_error = None
            break
        except SQLAlchemyError as exc:
            last_db_error = exc
            time.sleep(0.5)

    if last_db_error is not None:
        pytest.skip(f"Integration DB is unavailable: {last_db_error}")

    last_redis_error = None
    for _ in range(20):
        try:
            asyncio.run(r.ping())
            last_redis_error = None
            break
        except Exception as exc:  # noqa: BLE001
            last_redis_error = exc
            time.sleep(0.5)

    if last_redis_error is not None:
        pytest.skip(f"Integration Redis is unavailable: {last_redis_error}")


@pytest.fixture(scope="session", autouse=True)
def prepare_integration_schema(require_integration_mode, require_dependencies_up):
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_integration_state(require_integration_mode):
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())

    asyncio.run(r.flushdb())
    yield
