import streamlit as st
import requests
# import uuid
from streamlit_cookies_manager import EncryptedCookieManager

cookies = EncryptedCookieManager(
    prefix="rag_app",
    password="some_secret_key"
)

if not cookies.ready():
    st.stop()

if not st.session_state.get("token"):
    token = cookies.get("token")

    if token and token.strip() and not st.session_state.get("_logged_out"):  # add this check
        st.session_state.token = token
        st.session_state.role = cookies.get("role")
        st.session_state.username = cookies.get("username")
        st.session_state.session_id = st.session_state.username

LOGIN_URL = "http://localhost:8000/api/auth/login"

UPLOAD_URL = "http://localhost:8000/api/documents/upload"
DOCUMENTS_URL = "http://localhost:8000/api/documents/list"

API_URL = "http://localhost:8000/api/documents/chat"
HISTORY_URL = "http://localhost:8000/api/documents/chat/history"

st.set_page_config(
    page_title="RAG Support Chatbot",
    page_icon="💬",
    layout="centered",
)

# ---------- session defaults ----------
if "token" not in st.session_state:
    st.session_state.token = None

if "role" not in st.session_state:
    st.session_state.role = None

if "username" not in st.session_state:
    st.session_state.username = None

if "messages" not in st.session_state:
    st.session_state.messages = []

def login_user(username: str, password: str):
    try:
        response = requests.post(
            LOGIN_URL,
            data={
                "username": username,
                "password": password
            },
            timeout=30
        )
        return response
    except requests.RequestException as e:
        return e

def logout():
    cookies["token"] = ""
    cookies["role"] = ""
    cookies["username"] = ""
    cookies.save()

    # Don't use st.session_state.clear() — it wipes the cookie manager's internal state
    for key in ["token", "role", "username", "session_id", "messages"]:
        st.session_state.pop(key, None)

    st.session_state["_logged_out"] = True
    st.rerun()

def show_login_page():
    st.title("RAG Support Chatbot")
    st.subheader("Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if not username or not password:
            st.error("Enter both username and password.")
            return

        result = login_user(username, password)

        if isinstance(result, Exception):
            st.error(f"Backend connection failed: {result}")
            return

        if result.status_code != 200:
            st.error("Login failed.")
            return

        data = result.json()

        st.session_state.token = data.get("access_token")
        st.session_state.role = data.get("role")
        st.session_state.username = username

        # persist
        cookies["token"] = st.session_state.token
        cookies["role"] = st.session_state.role
        cookies["username"] = username
        cookies.save()
            
        st.session_state.session_id = username

        st.success(f"Logged in as {st.session_state.role}")
        st.rerun()


def show_admin_panel():
    st.title("Admin Panel")

    col1, col2 = st.columns([4, 1])
    with col1:
        st.write(f"Logged in as: **{st.session_state.username}** (Admin)")
    with col2:
        if st.button("Logout"):
            logout()

    st.divider()

    # -------- Upload Section --------
    st.subheader("Upload Document")

    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"]
    )

    if st.button("Upload"):
        if not uploaded_file:
            st.warning("Please select a file.")
        else:
            with st.spinner("Uploading document..."):
                result = upload_document(uploaded_file)

            if isinstance(result, Exception):
                st.error(f"Upload failed: {result}")
            elif result.status_code == 200:
                st.success("Document uploaded. Fetching status...")

                # auto fetch
                docs_result = fetch_documents()

                if not isinstance(docs_result, Exception) and docs_result.status_code == 200:
                    docs = docs_result.json()[-5:]

                    st.subheader("Latest Status")
                    for d in docs:
                        st.write(f"**{d['filename']}** → {d['status']}")
                else:
                    st.warning("Could not fetch updated status.")
            else:
                st.error(f"Upload failed: {result.text}")

    st.divider()

    # -------- Document Status Section --------
    st.subheader("Recent Documents")

    if st.button("Refresh Status"):
        result = fetch_documents()

        if isinstance(result, Exception):
            st.error(f"Failed to fetch documents: {result}")
            return

        if result.status_code != 200:
            st.error("Could not fetch document status.")
            return

        docs = result.json()

        if not docs:
            st.info("No documents found.")
            return

        docs = docs[-5:]

        for d in docs:
            st.write(f"**{d['filename']}** → {d['status']}")


def upload_document(file):
    try:
        headers = {
            "Authorization": f"Bearer {st.session_state.token}"
        }

        files = {
            "file": (file.name, file, "application/pdf")
        }

        response = requests.post(
            UPLOAD_URL,
            headers=headers,
            files=files,
            timeout=120
        )

        return response
    except requests.RequestException as e:
        return e


def fetch_documents():
    try:
        headers = {
            "Authorization": f"Bearer {st.session_state.token}"
        }

        response = requests.get(
            DOCUMENTS_URL,
            headers=headers,
            timeout=30
        )

        return response
    except requests.RequestException as e:
        return e
    
def show_customer_chat():
    st.title("Customer Chat")
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    col1, col2 = st.columns([4, 1])
    with col1:
        st.write(f"Logged in as: **{st.session_state.username}** (Customer)")
    with col2:
        if st.button("Logout"):
            logout()

    st.divider()

    # -------- Load history ONCE --------
    if not st.session_state.messages:
        result = fetch_chat_history()

        if not isinstance(result, Exception) and result.status_code == 200:
            history = result.json()

            existing = {(m["role"], m["content"]) for m in st.session_state.messages}

            for msg in history:
                key = (msg["role"], msg["content"])
                if key not in existing:
                    st.session_state.messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

    # -------- Display chat --------
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # -------- Input --------
    if prompt := st.chat_input("Ask your question..."):
        # user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        with st.chat_message("user"):
            st.markdown(prompt)

        # API call
        with st.spinner("Thinking..."):
            result = send_chat(prompt)

        if isinstance(result, Exception):
            answer = f"Error: {result}"
            sources = []
        elif result.status_code != 200:
            answer = f"Server error: {result.status_code} - {result.text}"
            sources = []
        else:
            data = result.json()
            answer = data.get("answer", "")
            sources = data.get("sources", [])

            if not answer.strip():
                answer = "I don't have that information in the documentation."

        # format sources
        source_text = ""
        if sources:
            source_text = "\n\n---\n**Sources:**\n\n" + "\n\n".join(
                [f"[Source {s['id']}]\n{s['text'][:200]}..." for s in sources]
            )

        final_response = answer + source_text

        # store assistant response
        st.session_state.messages.append({
            "role": "assistant",
            "content": final_response
        })

        # render assistant response
        with st.chat_message("assistant"):
            st.markdown(final_response)

    # disclaimer       
    st.caption("Responses are generated from uploaded documents only.")

def send_chat(question):
    try:
        headers = {
            "Authorization": f"Bearer {st.session_state.token}"
        }

        response = requests.post(
            API_URL,
            json={"question": question,
                "session_id": st.session_state.session_id},
            headers=headers,
            timeout=120
        )

        return response
    except requests.RequestException as e:
        return e


def fetch_chat_history():
    try:
        headers = {
            "Authorization": f"Bearer {st.session_state.token}"
        }

        response = requests.get(
            HISTORY_URL, 
            headers=headers,
            params={"session_id": st.session_state.session_id},
            timeout=30
        )

        return response
    except requests.RequestException as e:
        return e

# ---------- main routing ----------
if not st.session_state.token:
    show_login_page()
else:
    role = st.session_state.role

    if role == "admin":
        show_admin_panel()
    else:
        show_customer_chat()

