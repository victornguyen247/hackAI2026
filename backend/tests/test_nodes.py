import json
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from unittest.mock import patch
from app.models import User, RouteMap, Node

def setup_node_test_data(session: Session, test_user: dict):
    user = session.exec(select(User).where(User.username == "testuser")).first()
    rm = RouteMap(user_id=user.id, goal="Learn Python", is_public=False)
    session.add(rm)
    session.commit()
    session.refresh(rm)
    
    node = Node(route_map_id=rm.id, title="Python Basics", description="Start here", level=1, is_expandable=True)
    session.add(node)
    session.commit()
    session.refresh(node)
    return user, rm, node

def mock_expand_topic(topic: str, goal_context: str) -> list:
    return [
        {"title": "Variables", "description": "storing data", "is_expandable": False},
        {"title": "Loops", "description": "repeating tasks", "is_expandable": True}
    ]

@patch("app.services.service.Service.expand_topic", side_effect=mock_expand_topic)
def test_expand_node(mock_expand, client: TestClient, session: Session, test_user: dict):
    _, _, node = setup_node_test_data(session, test_user)
    
    response = client.post(f"/nodes/{node.id}/expand")
    assert response.status_code == 200
    
    # Check if parent node has_expanded is set to True
    session.refresh(node)
    assert node.has_expanded is True
    
    # Verify new nodes were created in the database
    new_nodes = session.exec(select(Node).where(Node.route_map_id == node.route_map_id, Node.level == node.level + 1)).all()
    assert len(new_nodes) == 2
    titles = [n.title for n in new_nodes]
    assert "Variables" in titles
    assert "Loops" in titles

def test_add_custom_resource(client: TestClient, session: Session, test_user: dict):
    _, _, node = setup_node_test_data(session, test_user)
    
    # Send custom resource
    response = client.post(
        f"/nodes/{node.id}/add-resource",
        params={
            "title": "My Custom Video",
            "url": "https://youtube.com/myvideo",
            "type": "video"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "My Custom Video"
    assert data[0]["url"] == "https://youtube.com/myvideo"
    
    # Verify in DB
    session.refresh(node)
    resources = json.loads(node.resources_json)
    assert len(resources) == 1
    assert resources[0]["title"] == "My Custom Video"

def test_toggle_node_complete(client: TestClient, session: Session, test_user: dict):
    user, _, node = setup_node_test_data(session, test_user)
    
    # Toggle complete
    response = client.post(
        f"/nodes/{node.id}/toggle-complete",
        params={"username": user.username}
    )
    
    assert response.status_code == 200
    assert response.json()["is_completed"] is True
    
    # Toggle uncomplete
    response = client.post(
        f"/nodes/{node.id}/toggle-complete",
        params={"username": user.username}
    )
    
    assert response.status_code == 200
    assert response.json()["is_completed"] is False
