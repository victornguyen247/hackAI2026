from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models import User

def test_register_user_success(client: TestClient, session: Session):
    response = client.post(
        "/register",
        params={
            "username": "newuser",
            "password": "securepassword",
            "first_name": "New",
            "last_name": "User"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert data["first_name"] == "New"
    
    # Verify in DB
    user = session.exec(select(User).where(User.username == "newuser")).first()
    assert user is not None
    assert user.password_hash == "securepassword"

def test_register_user_duplicate(client: TestClient, test_user: dict):
    # test_user is already created in conftest.py
    response = client.post(
        "/register",
        params={
            "username": "testuser",  # same username
            "password": "anotherpassword",
            "first_name": "Another",
            "last_name": "Name"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already exists"

def test_login_success(client: TestClient, test_user: dict):
    response = client.post(
        "/login",
        params={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_login_invalid_password(client: TestClient, test_user: dict):
    response = client.post(
        "/login",
        params={
            "username": "testuser",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401

def test_login_invalid_username(client: TestClient):
    response = client.post(
        "/login",
        params={
            "username": "nonexistent",
            "password": "password"
        }
    )
    assert response.status_code == 401
