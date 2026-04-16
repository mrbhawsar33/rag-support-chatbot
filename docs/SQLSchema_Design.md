# RAG-Powered Customer Support Chatbot: SQL Schema Design Document

**Created by:** Mayur Bhawsar, Yash Suthar, Pratham Patel

---

## Entity Relation Diagram


---

## Description of Relationships

**User → Document**

1. One user can upload many documents.
2. Each document belongs to exactly one user.

**User → Conversation**

1. One user can engage in many conversations (sessions/messages).
2. Each conversation entry belongs to exactly one user (session).

**Document → Document (Self-Referencing)**

1. One parent document can contain or be split into many child documents (hierarchy).
2. Each child document belongs to at most one parent document (optional relationship).

**Conversation → Conversation (Self-Referencing)**

1. One message can serve as a "cached response" for many subsequent questions.
2. Each specific message may point to one cached response for optimization.

---

## Data Dictionary

### 1. USER Table

| Column Name   | Data Type | is P Key | is F Key | FK Ref. Table | is Nullable | Description                              |
|---------------|-----------|----------|----------|---------------|-------------|------------------------------------------|
| User_id       | UUID      | Yes      | No       | -             | No          | Unique identifier for the user account.  |
| username      | String    | No       | No       | -             | No          | Unique login name for the user.          |
| password_hash | String    | No       | No       | -             | No          | Securely hashed user password.           |
| user_role     | Enum      | No       | No       | -             | No          | User access level ('admin' or 'customer'). |
| created_at    | Timestamp | No       | No       | -             | No          | Record of when the account was created.  |

---

### 2. DOCUMENT Table

| Column Name        | Data Type | is P Key | is F Key | FK Ref. Table | is Nullable | Description                              |
|--------------------|-----------|----------|----------|---------------|-------------|------------------------------------------|
| Document_id        | UUID      | Yes      | No       | -             | No          | Unique identifier for the document.      |
| uploaded_by        | UUID      | No       | Yes      | USER          | No          | Links the document to the uploader.      |
| parent_doc_id      | UUID      | No       | Yes      | DOCUMENT      | Yes         | Self-reference for document hierarchy.   |
| filename           | String    | No       | No       | -             | No          | The original name of the file.           |
| file_path          | String    | No       | No       | -             | No          | Storage location/path on the disk.       |
| status             | Enum      | No       | No       | -             | No          | Processing state (Uploaded to Error).    |
| chunk_count        | Integer   | No       | No       | -             | Yes         | Number of segments created from file.   |
| processing_time    | Float     | No       | No       | -             | Yes         | Time taken to process in seconds.        |
| document_structure | JSON      | No       | No       | -             | No          | Metadata regarding sections/pages.       |
| uploaded_at        | Timestamp | No       | No       | -             | No          | Date/Time of upload.                     |
| processed_at       | Timestamp | No       | No       | -             | Yes         | Date/Time processing was completed.      |

---

### 3. CONVERSATION Table

| Column Name       | Data Type | is P Key | is F Key | FK Ref. Table | is Nullable | Description                                  |
|-------------------|-----------|----------|----------|---------------|-------------|----------------------------------------------|
| Conversation_id   | UUID      | Yes      | No       | -             | No          | Unique identifier for the message.           |
| session_id        | UUID      | No       | No       | -             | No          | Groups messages within one chat session.     |
| user_id           | UUID      | No       | Yes      | USER          | No          | Links the message to a specific user.        |
| cached_response_id| UUID      | No       | Yes      | CONVERSATION  | Yes         | Self-reference to a cached FAQ answer.       |
| role              | Enum      | No       | No       | -             | No          | Origin of message ('user' or 'assistant').   |
| content           | Text      | No       | No       | -             | No          | The actual text of the message.              |
| sources           | JSON      | No       | No       | -             | No          | Cited doc chunks (ID, section, etc).         |
| metadata          | JSON      | No       | No       | -             | No          | Performance stats (latency, tokens).         |
| user_feedback     | Integer   | No       | No       | -             | Yes         | User rating (-1, 0, or 1).                   |
| is_cached_answer  | Boolean   | No       | No       | -             | No          | Flag for frequently asked questions.         |
| question_hash     | Integer   | No       | No       | -             | No          | Hash of user query for quick matching.       |
| created_at        | Timestamp | No       | No       | -             | No          | Date/Time message was sent.                  |

---

## Analytics Views (Logic Summary)

- **faq_analytics**: Aggregates the CONVERSATIONS table by `question_hash`. It identifies high-frequency questions (threshold ≥ 5) and calculates the user satisfaction (upvote rate) to determine if the current cached answer is effective.

- **document_analytics**: Joins DOCUMENTS with CONVERSATIONS by parsing the JSON `sources` field. This provides a "utility score" for documents based on how often the AI cites them to answer questions.

---

## Indexing Strategy

To maintain performance as the database grows, the following indexes are implemented:

- **Performance**: `idx_conversations_session` and `idx_conversations_user` ensure fast retrieval of chat histories.
- **Search**: `idx_conversations_question_hash` and `idx_conversations_cached` (partial index) allow the system to quickly find and serve pre-computed answers.
- **Management**: `idx_documents_status` and `idx_documents_user` allow admins to monitor processing pipelines and user-specific storage efficiently.

This ensures that searching for specific sessions or checking for cached FAQ hits remains O(1) or O(log n) efficiency.
