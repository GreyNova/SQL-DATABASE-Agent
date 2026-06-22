from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_test():
    print("Sending mock chat request to test Amazon database integration...")
    response = client.post(
        "/chat",
        json={
            "question": "Show me the top rated amazon products",
            "thread_id": "test_thread_123"
        }
    )
    print("Status Code:", response.status_code)
    
    # We can stream or just see what it returns.
    # Because it is a streaming endpoint, we can print its lines:
    for line in response.iter_lines():
        if line:
            print(line)

if __name__ == "__main__":
    run_test()
