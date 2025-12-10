import requests
import json

def test_chat_api():
    url = "http://127.0.0.1:8000/chat"
    # We need a token. Let's try to signup/login or just mock it if possible?
    # The API requires auth. I need to get a token first.
    
    # 1. Signup/Login to get token
    auth_url = "http://127.0.0.1:8000/auth/signup"
    user_data = {"email": "test_api_verif@example.com", "password": "password123"}
    
    try:
        requests.post(auth_url, json=user_data) # content-type json
    except:
        pass # Maybe already exists
        
    login_url = "http://127.0.0.1:8000/auth/login"
    # Login expects form data usually for OAuth2, but let's check the code.
    # checking login/page.tsx, it sends FormData.
    
    response = requests.post(login_url, data={"username": "test_api_verif@example.com", "password": "password123"})
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return

    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Send the symptom query
    chat_payload = {
        "query": "I am feeling tired and feverish",
        "session_id": None
    }
    
    print("Sending query to API...")
    try:
        chat_res = requests.post(url, json=chat_payload, headers=headers)
        if chat_res.status_code == 200:
            data = chat_res.json()
            print("\nAPI Response Keys:", data.keys())
            print("\nOutput Field Content:")
            print(data.get("output"))
            
            if "ayurveda_recommendations" in data:
                print("\n[WARNING] 'ayurveda_recommendations' field still exists! Backend might be old.")
            
            if "output" in data and "Ayurveda" in str(data["output"]):
                print("\n✅ API is returning unified output correctly.")
            else:
                print("\n❌ API 'output' does not contain expected consolidated content.")
        else:
            print(f"Chat API failed: {chat_res.status_code} {chat_res.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_chat_api()
