import requests
import json
import os

BASE_URL = "http://127.0.0.1:8000"
EMAIL = "testuser@example.com"
PASSWORD = "password123"

def test_auth_flow():
    print("\n--- Testing Auth Flow ---")
    
    # 1. Signup
    print("1. Signing up...")
    signup_res = requests.post(f"{BASE_URL}/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    if signup_res.status_code == 200:
        print("✅ Signup successful")
        token = signup_res.json()["access_token"]
    elif signup_res.status_code == 400 and "already registered" in signup_res.text:
        print("ℹ️ User already exists, logging in...")
        # 2. Login
        login_res = requests.post(f"{BASE_URL}/auth/login", data={"username": EMAIL, "password": PASSWORD})
        if login_res.status_code == 200:
            print("✅ Login successful")
            token = login_res.json()["access_token"]
        else:
            print(f"❌ Login failed: {login_res.text}")
            return None
    else:
        print(f"❌ Signup failed: {signup_res.text}")
        return None
        
    return token

def test_sessions(token):
    print("\n--- Testing Sessions ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create Session
    print("1. Creating new session...")
    res = requests.post(f"{BASE_URL}/sessions", json={"title": "Test Chat"}, headers=headers)
    if res.status_code == 200:
        session_id = res.json()["id"]
        print(f"✅ Session created: ID {session_id}")
    else:
        print(f"❌ Failed to create session: {res.text}")
        return None

    # 2. Send Message
    print(f"2. Sending message to session {session_id}...")
    chat_res = requests.post(f"{BASE_URL}/chat", json={"query": "Hello", "session_id": session_id}, headers=headers)
    if chat_res.status_code == 200:
        print("✅ Message sent successfully")
    else:
        print(f"❌ Message failed: {chat_res.text}")

    # 3. Get History
    print(f"3. Fetching history for session {session_id}...")
    hist_res = requests.get(f"{BASE_URL}/sessions/{session_id}/history", headers=headers)
    if hist_res.status_code == 200:
        history = hist_res.json()
        print(f"✅ History retrieved: {len(history)} messages")
        for msg in history:
            print(f"   - {msg['role']}: {msg['content'][:50]}...")
    else:
        print(f"❌ Failed to get history: {hist_res.text}")

def test_blockchain():
    print("\n--- Testing Blockchain Audit ---")
    if os.path.exists("audit_ledger.json"):
        with open("audit_ledger.json", "r") as f:
            ledger = json.load(f)
            print(f"✅ Ledger file found with {len(ledger)} blocks")
            latest = ledger[-1]
            print(f"   Latest Block Index: {latest['index']}")
            print(f"   Latest Action: {latest['data'].get('action')}")
            print(f"   Hash: {latest['hash']}")
    else:
        print("❌ Ledger file not found!")

if __name__ == "__main__":
    token = test_auth_flow()
    if token:
        test_sessions(token)
        test_blockchain()
