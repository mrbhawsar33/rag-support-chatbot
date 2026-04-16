import chainlit as cl
import httpx

LOGIN_URL = "http://localhost:8000/api/auth/login"
API_URL = "http://localhost:8000/api/documents/chat"
HISTORY_URL = "http://localhost:8000/api/documents/chat/history"
UPLOAD_URL = "http://localhost:8000/api/documents/upload"
DOCUMENTS_URL = "http://localhost:8000/api/documents/list"



@cl.on_message
async def main(message: cl.Message):
    role = cl.user_session.get("role")

    if role == "admin":
        await cl.Message(content="Admin cannot use chat. Use upload instead.").send()
        return
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        token = cl.user_session.get("token")

        headers = {
            "Authorization": f"Bearer {token}"
        }

        response = await client.post(
            API_URL,
            json={"question": message.content},
            headers=headers
        )

    data = response.json()

    answer = data.get("answer")
    if not answer or answer.strip() == "":
        answer = "I don't have that information in the documentation."
    
    sources = data.get("sources", [])

    # combine into one response
    source_text = ""
    if sources:
        source_text = "\n\n---\n**Sources:**\n\n" + "\n\n".join(
            [f"[Source {s['id']}]\n{s['text'][:200]}..." for s in sources]
        )

    final_response = answer + source_text

    await cl.Message(content=final_response).send()

@cl.on_chat_start
async def load_history():
    async with httpx.AsyncClient() as client:
        response = await client.get(HISTORY_URL)

    history = response.json()

    for msg in history:
        await cl.Message(
            content=msg["content"],
            author=msg["role"]
        ).send()

@cl.on_chat_start
async def upload_prompt():
    files = await cl.AskFileMessage(
        content="Upload a document (PDF)",
        accept=["application/pdf"],
        max_size_mb=10,
        timeout=180
    ).send()

    if not files:
        return

    file = files[0]

    async with httpx.AsyncClient(timeout=120.0) as client:
        token = cl.user_session.get("token")

        headers = {
            "Authorization": f"Bearer {token}"
        }

        with open(file.path, "rb") as f:
            response = await client.post(
                UPLOAD_URL,
                files={"file": (file.name, f, "application/pdf")},
                headers=headers
            )


    if response.status_code == 200:

        await cl.Message(
            content="Document uploaded. Processing may take ~30 seconds before it is available for queries."
        ).send()

        # fetch and show status
        async with httpx.AsyncClient() as client:
            docs_response = await client.get(
                DOCUMENTS_URL,
                headers=headers
            )

            if docs_response.status_code == 200:
                docs = docs_response.json()

                docs = docs[-5:]  # last 5 documents only

                status_text = "\n".join(
                    [f"{d['filename']} → {d['status']}" for d in docs]
                )

                await cl.Message(
                    content=f"**Document Status:**\n\n{status_text}"
                ).send()
            else:
                await cl.Message(
                    content="Could not fetch document status."
                ).send()

    else:
        await cl.Message(content=f"Upload failed: {response.text}").send()


@cl.on_chat_start
async def start():
    # ask username
    username_msg = await cl.AskUserMessage(
        content="Enter username:"
    ).send()
    
    username = username_msg['output']

    if not username:
        await cl.Message(content="Login cancelled").send()
        return

    # ask password
    password_msg = await cl.AskUserMessage(
        content="Enter password:"
    ).send()

    password = password_msg['output']

    # call backend login
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LOGIN_URL,
            data={
                "username": username,
                "password": password
            }
        )

    if response.status_code != 200:
        await cl.Message(content="Login failed").send()
        return

    data = response.json()

    token = data["access_token"]

    role = data.get("role")

    # store in session
    cl.user_session.set("token", token)
    cl.user_session.set("role", role)

    await cl.Message(content=f"Logged in as {role}").send()
    role = cl.user_session.get("role")

    if role == "admin":
        await cl.Message(content="Admin Panel Access").send()
    else:
        await cl.Message(content="Customer Chat Access").send()