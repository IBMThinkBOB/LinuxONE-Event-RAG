import requests

def query_qwen(prompt):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen",
            "prompt": prompt,
            "stream": False
        }
    )

    return response.json()["response"]