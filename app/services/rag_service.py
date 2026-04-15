from app.services.reranker_service import RerankerService


class RAGService:
    def __init__(self, chroma_client, embedding_service, llm_service):
        self.chroma_client = chroma_client
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.reranker = RerankerService()

    def generate_answer(self, query: str):
        # embed query
        query_embedding = self.embedding_service(query)

        # retrieve from chroma
        results = self.chroma_client.query(
            query_embeddings=[query_embedding],
            n_results=5
        )

        documents = results["documents"][0]

        # remove duplicates
        documents = list(dict.fromkeys(documents))
        
        # rerank
        reranked = self.reranker.rerank(query, documents, top_k=3)
        top_documents = [doc for doc, _ in reranked]

        # reverse repacking
        reversed_docs = list(reversed(top_documents))

        # build context
        context_blocks = []

        for i, doc in enumerate(reversed_docs):
            context_blocks.append(f"[Source {i+1}]\n{doc}")

        context = "\n\n".join(context_blocks)

        # build prompt
        prompt = f"""
        You are a professional customer support assistant.

        CRITICAL RULES:
        1. Answer ONLY using the provided context
        2. Use only information explicitly present in the context
        3. Keep the answer concise and clear
        4. You MUST include citations using [Source X]
        5. Do NOT invent information or sources
        6. If the answer is not in the context, say:
        "I don't have that information in the documentation."

        CONTEXT:
        {context}

        QUESTION:
        {query}

        ANSWER:
        """
        # call LLM
        answer = self.llm_service(prompt)

        return {
            "answer": answer,
            "sources": [
                {"id": i+1, "text": doc}
                for i, doc in enumerate(reversed_docs)
            ]
        }