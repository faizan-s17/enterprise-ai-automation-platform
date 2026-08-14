"""Shared fixtures for the test suite.

Tests run against an isolated in-memory SQLite database via a dependency
override, never the developer's own platform.db — the app's own lifespan
(which would touch the real database and reseed it) is never triggered
because TestClient only runs startup/shutdown inside a `with` block, and
nothing here uses one.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Role, User

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _fresh_schema():
    """Runs before every test (autouse fixtures resolve before non-autouse
    ones in the same scope), so nothing needs to remember to request it."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _no_live_ai(monkeypatch):
    """Force every test onto the deterministic local AI fallback, regardless
    of whatever API keys happen to be in the developer's own .env. Without
    this, running the suite locally with a real key configured would make
    real API calls and produce non-deterministic assertions."""
    from app.config import settings

    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def make_user(db, email: str, password: str, role: Role) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=email.split("@")[0].title(),
        department="Test",
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


CREDENTIALS = {
    "admin": ("admin@test.local", "Admin@12345", Role.ADMIN),
    "manager": ("manager@test.local", "Manager@12345", Role.MANAGER),
    "analyst": ("analyst@test.local", "Analyst@12345", Role.ANALYST),
    "viewer": ("viewer@test.local", "Viewer@12345", Role.VIEWER),
}


@pytest.fixture
def users(db):
    """One seeded user per role, keyed by role name."""
    return {
        key: make_user(db, email, password, role)
        for key, (email, password, role) in CREDENTIALS.items()
    }


def _login(client: TestClient, email: str, password: str) -> dict:
    resp = client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def tokens(client, users):
    """Auth headers for each seeded role, keyed the same way as `users`."""
    return {
        key: _login(client, email, password)
        for key, (email, password, _role) in CREDENTIALS.items()
    }
