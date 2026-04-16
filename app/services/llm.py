import json
import requests
import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"


def generate_answer(prompt: str):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
    )

    if response.status_code != 200:
        raise Exception(f"LLM error: {response.text}")

    data = response.json()
    return data["response"]


# not used currently
# def stream_answer(prompt: str):
#     with httpx.stream(
#         "POST",
#         OLLAMA_URL,
#         json={
#             "model": MODEL,
#             "prompt": prompt,
#             "stream": True
#         },
#         timeout=60.0
#     ) as response:

#         if response.status_code != 200:
#             raise Exception(f"LLM error: {response.text}")

#         for line in response.iter_lines():
#             if line:
#                 try:
#                     data = json.loads(line)
#                     token = data.get("response", "")
#                     if token:
#                         yield token
#                 except:
#                     continue