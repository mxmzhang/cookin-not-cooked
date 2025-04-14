import requests

def test_gemini_api(api_key):
    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": "Say hello"}]}]
    }
    
    response = requests.post(url, headers=headers, params={"key": api_key}, json=data)
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")

# Replace with your API key
api_key = "AIzaSyBQZlkfgNicFHPQaL9wO7bhlkE0Q2y1HHA"
test_gemini_api(api_key)