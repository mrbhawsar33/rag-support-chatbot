# RAG-powered-customer-support-chatbot
AI-powered customer support chatbot that answers questions by retrieving information from company knowledge documents.


# Tech Spec Document:
https://tree-carol-f18.notion.site/ebd//3395eedc20cd809bbacbcad306fba02f

# Structure:
```
rag-support-chatbot/
├── app/
│   ├── api/
│   │   ├── auth.py
│   │   └── document.py
│   ├── core/
│   ├── models/
│   │   ├── conversation.py
│   │   ├── document.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── chat_request.py
│   │   ├── document.py
│   │   └── user.py
│   ├── services/
│   │   ├── document_processor.py
│   │   ├── embedding.py
│   │   ├── llm.py
│   │   ├── rag_service.py
│   │   ├── reranker_service.py
│   │   ├── scheduler.py
│   │   └── vector_store.py
│   └── main.py
├── docs/
├── ui/
│   ├── chainlit_app.py
│   └── streamlit_app.py
├── uploads/
├── venv/
├── .env
├── .gitignore
├── docker-compose.yml
├── README.md
└── requirements.txt
```