from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from typing import List, Optional, Dict
import json
import requests
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

class ChatMessage(BaseModel):
    role: str # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    goal_context: str

from .models import engine, create_db_and_tables, User, RouteMap, Node, UserProgress, NodeLink
from .services.service import Service

app = FastAPI(title="Learning Route Advisor API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    import os
    if not os.environ.get("GEMINI_API_KEY"):
        print("WARNING: GEMINI_API_KEY is not set. Roadmap generation will fail.")
    create_db_and_tables()

def get_session():
    with Session(engine) as session:
        yield session

@app.post("/register", response_model=User)
def register(username: str, password: str, first_name: str, last_name: str, linkedin: Optional[str] = None, social_link: Optional[str] = None, session: Session = Depends(get_session)):
    # Check if user already exists
    statement = select(User).where(User.username == username)
    if session.exec(statement).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    user = User(
        username=username, 
        password_hash=password, # In a real app, use proper hashing
        first_name=first_name,
        last_name=last_name,
        linkedin=linkedin,
        social_link=social_link
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.post("/login")
def login(username: str, password: str, session: Session = Depends(get_session)):
    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()
    if not user or user.password_hash != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"status": "success", "username": user.username}

@app.post("/chat")
def chat_agent(request: ChatRequest):
    try:
        # Convert Pydantic messages to dicts for the service
        messages_dict = [{"role": m.role, "content": m.content} for m in request.messages]
        response_text = Service.chat(messages_dict, request.goal_context)
        return {"response": response_text}
    except Exception as e:
        print(f"DEBUG: Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Chat service failure")

@app.get("/users/{username}", response_model=User)
def get_user(username: str, session: Session = Depends(get_session)):
    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/users/{username}", response_model=User)
def update_user(username: str, first_name: str, last_name: str, linkedin: Optional[str] = None, social_link: Optional[str] = None, password: Optional[str] = None, session: Session = Depends(get_session)):
    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.first_name = first_name
    user.last_name = last_name
    user.linkedin = linkedin
    user.social_link = social_link
    if password:
        user.password_hash = password
        
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.get("/users/{username}/route-maps", response_model=List[RouteMap])
def get_user_route_maps(username: str, session: Session = Depends(get_session)):
    user_stmt = select(User).where(User.username == username)
    user = session.exec(user_stmt).first()
    if not user:
        return []
    
    stmt = select(RouteMap).where(RouteMap.user_id == user.id)
    return session.exec(stmt).all()

@app.delete("/route-maps/{route_id}")
def delete_route_map(route_id: int, session: Session = Depends(get_session)):
    route_map = session.get(RouteMap, route_id)
    if not route_map:
        raise HTTPException(status_code=404, detail="Route map not found")
    
    # Delete associated nodes, their progress, and links
    for node in route_map.nodes:
        # Delete links where this node is parent or child
        link_stmt = select(NodeLink).where((NodeLink.parent_id == node.id) | (NodeLink.child_id == node.id))
        for link in session.exec(link_stmt).all():
            session.delete(link)
            
        # UserProgress usually has a foreign key to node, so delete progress first
        prog_stmt = select(UserProgress).where(UserProgress.node_id == node.id)
        for progress in session.exec(prog_stmt).all():
            session.delete(progress)
        session.delete(node)
    
    session.delete(route_map)
    session.commit()
    return {"status": "success"}

@app.post("/route-maps/{route_id}/toggle-visibility")
def toggle_route_visibility(route_id: int, session: Session = Depends(get_session)):
    route_map = session.get(RouteMap, route_id)
    if not route_map:
        raise HTTPException(status_code=404, detail="Route map not found")
    
    print(f"DEBUG: Toggling visibility for map {route_id}. Old status: {route_map.is_public}", flush=True)
    route_map.is_public = not route_map.is_public
    session.add(route_map)
    session.commit()
    session.refresh(route_map)
    print(f"DEBUG: Toggling visibility for map {route_id}. New status: {route_map.is_public}", flush=True)
    return {"status": "success", "is_public": route_map.is_public}
    
@app.get("/users/search/{search_username}")
def search_user(search_username: str, session: Session = Depends(get_session)):
    user_stmt = select(User).where(User.username == search_username)
    user = session.exec(user_stmt).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get public maps
    map_stmt = select(RouteMap).where(RouteMap.user_id == user.id, RouteMap.is_public == True)
    public_maps = session.exec(map_stmt).all()
    
    return {
        "user": {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "linkedin": user.linkedin,
            "social_link": user.social_link
        },
        "public_maps": public_maps
    }

@app.post("/route-maps/{route_id}/clone")
def clone_route_map(route_id: int, current_username: str, session: Session = Depends(get_session)):
    # 1. Get original map
    original_map = session.get(RouteMap, route_id)
    if not original_map or not original_map.is_public:
        raise HTTPException(status_code=404, detail="Route map not found or not public")
    
    # 2. Get current user
    user_stmt = select(User).where(User.username == current_username)
    current_user = session.exec(user_stmt).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 3. Create new map
    root_id = original_map.root_map_id or original_map.id
    new_map = RouteMap(
        user_id=current_user.id,
        goal=original_map.goal,
        description=original_map.description,
        is_public=False,
        creator_username=original_map.creator_username or original_map.user.username,
        clones_count=0,
        root_map_id=root_id
    )
    session.add(new_map)
    session.commit()
    session.refresh(new_map)
    
    # 4. Increment root map's clones_count (Centralized tracking on Origin)
    root_map = session.get(RouteMap, root_id)
    if root_map:
        root_map.clones_count += 1
        session.add(root_map)
    
    # 5. Clone nodes
    node_stmt = select(Node).where(Node.route_map_id == route_id)
    original_nodes = session.exec(node_stmt).all()
    
    node_map = {} # {old_id: new_id}
    
    # First pass: Create all nodes
    for old_node in original_nodes:
        new_node = Node(
            route_map_id=new_map.id,
            title=old_node.title,
            description=old_node.description,
            level=old_node.level,
            x=old_node.x,
            y=old_node.y,
            is_expandable=old_node.is_expandable,
            has_expanded=old_node.has_expanded,
            resources_json=old_node.resources_json
        )
        session.add(new_node)
        session.commit()
        session.refresh(new_node)
        node_map[old_node.id] = new_node.id
    
    # Second pass: Create links
    if node_map:
        link_stmt = select(NodeLink).where(NodeLink.parent_id.in_(node_map.keys()))
        original_links = session.exec(link_stmt).all()
        
        for link in original_links:
            # Only add link if both nodes were cloned
            if link.child_id in node_map:
                new_link = NodeLink(
                    parent_id=node_map[link.parent_id],
                    child_id=node_map[link.child_id]
                )
                session.add(new_link)
        
    session.commit()
    return new_map

@app.post("/onboarding/", response_model=RouteMap)
def onboarding(username: str, goal: str, session: Session = Depends(get_session)):
    try:
        # 🚀 Summarize goal into a short title
        short_goal = Service.summarize_goal(goal)
        if short_goal == "":
            #go back to page describe goal
            raise HTTPException(status_code=400, detail="Goal is empty or not a actual goal")

        print(f"DEBUG: Summarized goal '{goal}' -> '{short_goal}'", flush=True)

        # Get user
        statement = select(User).where(User.username == username)
        user = session.exec(statement).first()
        if not user:
            # Auto-create user for demo purposes
            user = User(username=username, password_hash="dummy")
            session.add(user)
            session.commit()
            session.refresh(user)
        
        # Create RouteMap
        route_map = RouteMap(
            user_id=user.id, 
            goal=short_goal, 
            is_public=False,
            creator_username=username
        )
        session.add(route_map)
        session.commit()
        session.refresh(route_map)
              # PROMPT 1: Root and overview (Phase 1)
        print(f"DEBUG: Phase 1 Generation for: {goal}", flush=True)
        initial_nodes = Service.generate_learning_route(goal)
        
        if not initial_nodes:
            print("DEBUG WARNING: No nodes were generated by the API!", flush=True)

        # Map title to Node for Phase 1 linking
        title_to_node = {}
        for rn in initial_nodes:
            # Check for existing nodes with same title in map? Doesn't apply to first call but good for consistency
            node = Node(
                route_map_id=route_map.id,
                title=rn["title"],
                description=rn["description"],
                level=rn["level"],
                is_expandable=rn.get("is_expandable", True)
            )
            session.add(node)
            session.commit()
            session.refresh(node)
            title_to_node[rn["title"]] = node

        # Link Phase 1 parents
        for rn in initial_nodes:
            if rn.get("parent_title"):
                child = title_to_node.get(rn["title"])
                parent = title_to_node.get(rn["parent_title"])
                if child and parent:
                    link = NodeLink(parent_id=parent.id, child_id=child.id)
                    session.add(link)
        
        session.commit()
        session.refresh(route_map)
        return route_map
    except Exception as e:
        print(f"DEBUG ERROR in onboarding: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/route-maps/{route_id}/nodes", response_model=List[Node])
def get_route_nodes(route_id: int, session: Session = Depends(get_session)):
    statement = select(Node).where(Node.route_map_id == route_id)
    nodes = session.exec(statement).all()
    return nodes

@app.get("/route-maps/{route_id}/edges")
def get_route_edges(route_id: int, session: Session = Depends(get_session)):
    # Get all nodes in this map
    nodes_stmt = select(Node.id).where(Node.route_map_id == route_id)
    node_ids = session.exec(nodes_stmt).all()
    
    # Get all links where parent or child is in this map
    links_stmt = select(NodeLink).where(NodeLink.parent_id.in_(node_ids))
    return session.exec(links_stmt).all()

@app.post("/nodes/{node_id}/expand")
def expand_node(node_id: int, session: Session = Depends(get_session)):
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    if node.has_expanded:
        return []

    route_map = session.get(RouteMap, node.route_map_id)
    
    # Generate sub-nodes (Phase 2/3)
    raw_sub_nodes = Service.expand_topic(node.title, route_map.goal)
    
    if not raw_sub_nodes:
        node.is_expandable = False
        node.has_expanded = True
        session.add(node)
        session.commit()
        return []

    new_nodes = []
    for rn in raw_sub_nodes:
        # 🚀 DAG Check: Does a node with this title already exist in this RouteMap?
        existing_stmt = select(Node).where(Node.route_map_id == node.route_map_id, Node.title == rn["title"])
        existing_node = session.exec(existing_stmt).first()
        
        target_node = None
        if existing_node:
            print(f"DEBUG: Found existing node for '{rn['title']}', linking instead of creating.", flush=True)
            target_node = existing_node
        else:
            target_node = Node(
                route_map_id=node.route_map_id,
                title=rn["title"],
                description=rn["description"],
                level=node.level + 1,
                is_expandable=rn.get("is_expandable", True)
            )
            session.add(target_node)
            session.commit()
            session.refresh(target_node)
            new_nodes.append(target_node)
        
        # Create link (avoid duplicate links)
        link_stmt = select(NodeLink).where(NodeLink.parent_id == node.id, NodeLink.child_id == target_node.id)
        if not session.exec(link_stmt).first():
            link = NodeLink(parent_id=node.id, child_id=target_node.id)
            session.add(link)
    
    node.has_expanded = True
    session.add(node)
    session.commit()
    return new_nodes

@app.get("/nodes/{node_id}/resources")
def get_node_resources(node_id: int, username: Optional[str] = None, session: Session = Depends(get_session)):
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    resources = []
    if node.resources_json:
        resources = json.loads(node.resources_json)
    else:
        # Fetch from Claude
        route_map = session.get(RouteMap, node.route_map_id)
        print(f"DEBUG: Resources missing for {node.title}, fetching from LLM...")
        resources = Service.get_resources_for_topic(node.title, route_map.goal)
        
        # Check for aliveness
        for res in resources:
            if res.get("type", "").lower() == "video":
                try:
                    headers = {"User-Agent": "Mozilla/5.0"}
                    head_res = requests.head(res.get("url"), headers=headers, timeout=3, allow_redirects=True)
                    # Some sites block HEAD (405) or some other codes but are still alive
                    res["is_alive"] = head_res.status_code < 400 or head_res.status_code == 405
                except:
                    res["is_alive"] = False
            else:
                res["is_alive"] = True

        node.resources_json = json.dumps(resources)
        session.add(node)
        session.commit()
    
    # Check user progress for these resources
    completed_urls = []
    if username:
        user_stmt = select(User).where(User.username == username)
        user = session.exec(user_stmt).first()
        if user:
            prog_stmt = select(UserProgress).where(UserProgress.node_id == node_id, UserProgress.user_id == user.id)
            progress = session.exec(prog_stmt).first()
            if progress and progress.completed_resources_json:
                completed_urls = json.loads(progress.completed_resources_json)
    
    for res in resources:
        res["is_completed"] = res.get("url") in completed_urls
        
    return resources

@app.post("/nodes/{node_id}/refresh-resources")
def refresh_node_resources(node_id: int, username: Optional[str] = None, session: Session = Depends(get_session)):
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Force fetch from LLM
    route_map = session.get(RouteMap, node.route_map_id)
    print(f"DEBUG: Refreshing resources for {node.title}...", flush=True)
    resources = Service.get_resources_for_topic(node.title, route_map.goal)
    
    # Check for aliveness
    for res in resources:
        if res.get("type", "").lower() == "video":
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                head_res = requests.head(res.get("url"), headers=headers, timeout=3, allow_redirects=True)
                res["is_alive"] = head_res.status_code < 400 or head_res.status_code == 405
            except:
                res["is_alive"] = False
        else:
            res["is_alive"] = True

    node.resources_json = json.dumps(resources)
    session.add(node)
    session.commit()
    session.refresh(node)
    
    # Check user progress for these resources
    completed_urls = []
    if username:
        user_stmt = select(User).where(User.username == username)
        user = session.exec(user_stmt).first()
        if user:
            prog_stmt = select(UserProgress).where(UserProgress.node_id == node_id, UserProgress.user_id == user.id)
            progress = session.exec(prog_stmt).first()
            if progress and progress.completed_resources_json:
                completed_urls = json.loads(progress.completed_resources_json)
    
    for res in resources:
        res["is_completed"] = res.get("url") in completed_urls
        
    return resources

@app.post("/nodes/{node_id}/add-resource")
def add_custom_resource(node_id: int, title: str, url: str, type: str, session: Session = Depends(get_session)):
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    current_resources = json.loads(node.resources_json or "[]")
    
    new_resource = {
        "title": title,
        "url": url,
        "type": type.lower(),
        "description": "User added resource",
        "is_alive": True # Assume alive for user-added
    }
    
    # Add to the TOP of the list
    current_resources.insert(0, new_resource)
    
    node.resources_json = json.dumps(current_resources)
    session.add(node)
    session.commit()
    session.refresh(node)
    
    return current_resources

@app.post("/nodes/{node_id}/toggle-resource")
def toggle_resource_complete(node_id: int, username: str, resource_url: str, session: Session = Depends(get_session)):
    user_stmt = select(User).where(User.username == username)
    user = session.exec(user_stmt).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    stmt = select(UserProgress).where(UserProgress.node_id == node_id, UserProgress.user_id == user.id)
    progress = session.exec(stmt).first()
    
    if not progress:
        progress = UserProgress(user_id=user.id, node_id=node_id, is_completed=False, completed_resources_json="[]")
        session.add(progress)
        session.commit()
        session.refresh(progress)

    completed_urls = json.loads(progress.completed_resources_json or "[]")
    if resource_url in completed_urls:
        completed_urls.remove(resource_url)
    else:
        completed_urls.append(resource_url)
        
    progress.completed_resources_json = json.dumps(completed_urls)
    session.add(progress)
    session.commit()
    return {"status": "success", "is_completed": resource_url in completed_urls}

@app.post("/nodes/{node_id}/toggle-complete")
def toggle_node_complete(node_id: int, username: str, session: Session = Depends(get_session)):
    user_stmt = select(User).where(User.username == username)
    user = session.exec(user_stmt).first()
    
    stmt = select(UserProgress).where(UserProgress.node_id == node_id, UserProgress.user_id == user.id)
    progress = session.exec(stmt).first()
    
    if progress:
        progress.is_completed = not progress.is_completed
    else:
        progress = UserProgress(user_id=user.id, node_id=node_id, is_completed=True)
    
    session.add(progress)
    session.commit()
    
    # Auto-collapse logic
    if progress.is_completed:
        # 1. Check if this node is a parent and all its children are done
        node = session.get(Node, node_id)
        child_links = session.exec(select(NodeLink).where(NodeLink.parent_id == node_id)).all()
        if child_links:
            all_children_done = True
            for link in child_links:
                child_prog = session.exec(select(UserProgress).where(
                    UserProgress.node_id == link.child_id, 
                    UserProgress.user_id == user.id
                )).first()
                if not child_prog or not child_prog.is_completed:
                    all_children_done = False
                    break
            
            if all_children_done:
                node.is_collapsed = True
                session.add(node)
        
        # 2. Check if this node is a child and its parent + siblings are all done
        parent_links = session.exec(select(NodeLink).where(NodeLink.child_id == node_id)).all()
        for p_link in parent_links:
            parent = session.get(Node, p_link.parent_id)
            parent_prog = session.exec(select(UserProgress).where(
                UserProgress.node_id == parent.id, 
                UserProgress.user_id == user.id
            )).first()
            
            if parent_prog and parent_prog.is_completed:
                siblings = session.exec(select(NodeLink).where(NodeLink.parent_id == parent.id)).all()
                all_sibs_done = True
                for s_link in siblings:
                    sib_prog = session.exec(select(UserProgress).where(
                        UserProgress.node_id == s_link.child_id, 
                        UserProgress.user_id == user.id
                    )).first()
                    if not sib_prog or not sib_prog.is_completed:
                        all_sibs_done = False
                        break
                
                if all_sibs_done:
                    parent.is_collapsed = True
                    session.add(parent)
        
        session.commit()

    return {"status": "success", "is_completed": progress.is_completed}

@app.post("/nodes/{node_id}/position")
def update_node_position(node_id: int, x: float, y: float, session: Session = Depends(get_session)):
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node.x = x
    node.y = y
    session.add(node)
    session.commit()
    return {"status": "success"}

@app.post("/nodes/{node_id}/toggle-collapse")
def toggle_node_collapse(node_id: int, session: Session = Depends(get_session)):
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node.is_collapsed = not node.is_collapsed
    session.add(node)
    session.commit()
    return {"status": "success", "is_collapsed": node.is_collapsed}

@app.get("/users/{username}/progress")
def get_user_progress(username: str, session: Session = Depends(get_session)):
    user_stmt = select(User).where(User.username == username)
    user = session.exec(user_stmt).first()
    if not user:
        return []
    
    stmt = select(UserProgress).where(UserProgress.user_id == user.id)
    progress_list = session.exec(stmt).all()
    return {p.node_id: p.is_completed for p in progress_list}
