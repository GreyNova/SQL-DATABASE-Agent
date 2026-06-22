import httpx
import json

def test_stream():
    url = "http://localhost:8000/chat/stream"
    payload = {
        "question": "Show me the top rated amazon products",
        "thread_id": "test_stream_123",
        "sample_size": 5
    }
    with httpx.stream("POST", url, json=payload, timeout=60.0) as response:
        print(f"Status Code: {response.status_code}")
        for line in response.iter_lines():
            if line:
                print(line)

if __name__ == "__main__":
    test_stream()
