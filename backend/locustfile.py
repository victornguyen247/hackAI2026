from locust import HttpUser, task, between

class LearningAdvisorUser(HttpUser):
    wait_time = between(1, 5) # Wait 1-5 seconds between tasks
    
    def on_start(self):
        # Register a new user for the test session if needed, 
        # or just login as a known test user.
        # Here we'll just search for a user to simulate generic traffic
        pass

    @task(3)
    def index_search_user(self):
        """Simulate a user searching for another user's public maps"""
        self.client.get("/users/search/testuser", name="/users/search/[username]")

    @task(2)
    def view_route_maps(self):
        """Simulate fetching route maps for a user"""
        self.client.get("/users/testuser/route-maps", name="/users/[username]/route-maps")

