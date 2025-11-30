from api import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_crash():
    print("Testing Signup...")
    try:
        response = client.post("/auth/signup", json={"email": "crash_test@example.com", "password": "password"})
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"CRASHED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_crash()
