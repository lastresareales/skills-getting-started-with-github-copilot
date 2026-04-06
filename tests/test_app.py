import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    from src.app import activities
    
    # Store original state
    original_state = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    activities.clear()
    activities.update(original_state)


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_list(self, client):
        """Should return list of all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
    
    def test_activities_have_correct_structure(self, client):
        """Each activity should have required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, details in data.items():
            assert "description" in details
            assert "schedule" in details
            assert "max_participants" in details
            assert "participants" in details
            assert isinstance(details["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_participant_succeeds(self, client, reset_activities):
        """Should successfully sign up a new participant"""
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "new.student@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "new.student@mergington.edu" in data["message"]
    
    def test_signup_adds_participant_to_list(self, client, reset_activities):
        """Participant should be added to activity's participant list"""
        email = "test.student@mergington.edu"
        client.post(
            "/activities/Programming%20Class/signup",
            params={"email": email}
        )
        
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Programming Class"]["participants"]
    
    def test_signup_duplicate_fails(self, client, reset_activities):
        """Should reject duplicate signups for same activity"""
        email = "duplicate.test@mergington.edu"
        activity = "Gym%20Class"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_signup_nonexistent_activity_fails(self, client, reset_activities):
        """Should return 404 for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_at_max_capacity_fails(self, client, reset_activities):
        """Should reject signup when activity is at max capacity"""
        from src.app import activities
        
        # Find a small activity and fill it
        activity_name = "Chess Club"
        activity = activities[activity_name]
        max_participants = activity["max_participants"]
        
        # Fill the activity to capacity
        for i in range(max_participants):
            activity["participants"].append(f"student{i}@mergington.edu")
        
        # Try to add one more - should fail
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": "extra.student@mergington.edu"}
        )
        assert response.status_code == 400
        assert "max capacity" in response.json()["detail"]
    
    def test_signup_multiple_different_activities_succeeds(self, client, reset_activities):
        """Same student can sign up for multiple different activities"""
        email = "multi.student@mergington.edu"
        
        response1 = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        response2 = client.post(
            "/activities/Programming%20Class/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify both signups took
        activities_response = client.get("/activities")
        data = activities_response.json()
        assert email in data["Chess Club"]["participants"]
        assert email in data["Programming Class"]["participants"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/signup endpoint"""
    
    def test_unregister_existing_participant_succeeds(self, client, reset_activities):
        """Should successfully unregister an existing participant"""
        email = "remove.me@mergington.edu"
        
        # First sign up
        client.post(
            "/activities/Chess%20Club/signup",
            params={"email": email}
        )
        
        # Then unregister
        response = client.delete(
            "/activities/Chess%20Club/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]
    
    def test_unregister_removes_from_list(self, client, reset_activities):
        """Participant should be removed from activity list"""
        email = "remove.test@mergington.edu"
        
        # Sign up
        client.post(
            "/activities/Programming%20Class/signup",
            params={"email": email}
        )
        
        # Unregister
        client.delete(
            "/activities/Programming%20Class/signup",
            params={"email": email}
        )
        
        # Verify removed
        activities_response = client.get("/activities")
        data = activities_response.json()
        assert email not in data["Programming Class"]["participants"]
    
    def test_unregister_nonexistent_participant_fails(self, client, reset_activities):
        """Should fail when trying to unregister non-registered student"""
        response = client.delete(
            "/activities/Gym%20Class/signup",
            params={"email": "never.signed.up@mergington.edu"}
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]
    
    def test_unregister_nonexistent_activity_fails(self, client, reset_activities):
        """Should return 404 for non-existent activity"""
        response = client.delete(
            "/activities/Fake%20Activity/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]


class TestRootEndpoint:
    """Tests for root endpoint"""
    
    def test_root_redirects_to_index(self, client):
        """Root path should redirect to static index"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]
