import requests

try:
    response = requests.get("http://127.0.0.1:9090/api/v1/app/version")
    print(f"API Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Version: {response.json()['version']}")
except Exception as e:
    print(f"API Error: {e}")