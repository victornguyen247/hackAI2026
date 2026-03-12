from fastapi.testclient import TestClient
from sqlmodel import Session, select
from unittest.mock import patch
from app.models import RouteMap, Node, User

# Mock responses for Gemini
def mock_summarize_goal(goal: str) -> str:
    return "Test Goal Summary"

def mock_generate_learning_route(goal: str) -> list:
    return [
        {
            "title": "Root Topic",
            "description": "The main topic",
            "parent_title": None,
            "level": 1,
            "is_expandable": True
        },
        {
            "title": "Sub Topic 1",
            "description": "A sub topic",
            "parent_title": "Root Topic",
            "level": 2,
            "is_expandable": True
        }
    ]

@patch("app.services.service.Service.summarize_goal", side_effect=mock_summarize_goal)
@patch("app.services.service.Service.generate_learning_route", side_effect=mock_generate_learning_route)
def test_onboarding_success(mock_generate, mock_summarize, client: TestClient, test_user: dict):
    response = client.post(
        "/onboarding/",
        params={
            "username": "testuser",
            "goal": "I want to learn testing"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["goal"] == "Test Goal Summary"
    assert data["creator_username"] == "testuser"
    assert "id" in data
    
    # Verify mock was called
    mock_summarize.assert_called_once_with("I want to learn testing")
    mock_generate.assert_called_once_with("I want to learn testing")

def test_get_user_route_maps(client: TestClient, session: Session, test_user: dict):
    # Add a dummy map for user
    user = session.exec(select(User).where(User.username == "testuser")).first()
    new_map = RouteMap(user_id=user.id, goal="Get Maps Test", creator_username="testuser")
    session.add(new_map)
    session.commit()
    
    response = client.get(f"/users/testuser/route-maps")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["goal"] == "Get Maps Test"

def test_toggle_visibility(client: TestClient, session: Session, test_user: dict):
    user = session.exec(select(User).where(User.username == "testuser")).first()
    new_map = RouteMap(user_id=user.id, goal="Visibility Test", is_public=False)
    session.add(new_map)
    session.commit()
    session.refresh(new_map)
    
    response = client.post(f"/route-maps/{new_map.id}/toggle-visibility")
    assert response.status_code == 200
    assert response.json()["is_public"] is True
    
    # Verify in DB
    updated_map = session.get(RouteMap, new_map.id)
    assert updated_map.is_public is True
