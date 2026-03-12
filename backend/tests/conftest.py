import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from app.main import app, get_session
# Import all models to ensure they are registered with SQLModel metadata
from app.models import User, RouteMap, Node, NodeLink, UserProgress

# Use an in-memory SQLite database for testing
sqlite_url = "sqlite://"
# Use StaticPool to keep the in-memory db alive across multiple connections in the same thread
from sqlalchemy.pool import StaticPool
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False}, poolclass=StaticPool)

@pytest.fixture(name="session")
def session_fixture():
    # Create tables before each test
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    # Drop them after
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(name="test_user")
def test_user_fixture(client: TestClient, session: Session):
    response = client.post(
        "/register",
        params={
            "username": "testuser",
            "password": "testpassword",
            "first_name": "Test",
            "last_name": "User"
        }
    )
    user_data = response.json()
    return user_data

