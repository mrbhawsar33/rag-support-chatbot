import requests


OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text:latest"


def get_embedding(text: str):
    response = requests.post(
        OLLAMA_EMBED_URL,
        json={
            "model": EMBED_MODEL,
            "prompt": text
        }
    )

    if response.status_code != 200:
        raise Exception(f"Embedding failed: {response.text}")

    data = response.json()
    return data["embedding"]