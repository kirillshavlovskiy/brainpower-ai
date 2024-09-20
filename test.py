import requests
import json

def test_deployment():
    url = "http://8000.brainpower-ai.net/sandbox/deploy_to_server/"
    headers = {
        "Content-Type": "application/json",
        "Origin": "http://localhost:3000"
    }
    data = {
        "container_id": "a09286c6dfdb",
        "user_id": "0",
        "file_name": "test_component"
    }

    print(f"Request Body: {json.dumps(data)}")

    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_deployment()