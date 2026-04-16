import re
import time
from app.services.reranker_service import RerankerService
# from app.services.llm import stream_answer

# decrease latency, skip HyDE
USE_HYDE = False

class RAGService:
    def __init__(self, chroma_client, embedding_service, llm_service):
        self.chroma_client = chroma_client
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.reranker = RerankerService()

    # def stream_answer(self, query: str):
       
    #     # Measure execution time
    #     start_time = time.time()

    #     if USE_HYDE:
    #         hyde_text = self.generate_hyde_query(query)

    #         # DEBUG
    #         print("=== ORIGINAL QUERY ===", query)
    #         print("=== HYDE QUERY ===", hyde_text[:300])

    #         # embed hypothetical query
    #         query_embedding = self.embedding_service(hyde_text)
    #     else:
    #         query_embedding = self.embedding_service(query)

    #     # retrieve from chroma
    #     results = self.chroma_client.query(
    #         query_embeddings=[query_embedding],
    #         n_results=3 # or 5
    #     )

    #     documents = results["documents"][0]

    #     # debug
    #     retrieval_count = len(documents)
    #     print("=== RETRIEVAL COUNT ===", retrieval_count)


    #     # remove duplicates
    #     documents = list(dict.fromkeys(documents))
        
    #     # re-ranker causing bottleneck, skipping for now
    #     # # rerank
    #     # reranked = self.reranker.rerank(query, documents, top_k=2) # uses original user query
    #     # top_documents = [doc for doc, _ in reranked]

    #     # # debug
    #     # rerank_count = len(top_documents)
    #     # print("=== RERANK COUNT ===", rerank_count)

    #     # reverse repacking
    #     reversed_docs = list(reversed(documents)) # top_documents if using reranker

    #     # compress context
    #     compressed_docs = self.compress_context(query, reversed_docs) # uses original user query
        
    #     # build context
    #     context_blocks = []

    #     for i, doc in enumerate(compressed_docs):
    #         context_blocks.append(f"[Source {i+1}]\n{doc}")

    #     context = "\n\n".join(context_blocks)

    #     # build prompt uses original user query
    #     prompt = f"""
    #     You are a strict customer support assistant.

    #     CRITICAL RULES:
    #     1. Answer ONLY using the provided context
    #     2. Do NOT infer, assume, or expand beyond the context
    #     3. If exact answer is not explicitly stated, say:
    #     "I don't have that information in the documentation."
    #     4. Every statement must be directly supported by context
    #     5. Do NOT add explanations, background, or reasoning
    #     6. Use citations ONLY when exact match exists

    #     CONTEXT:
    #     {context}

    #     QUESTION:
    #     {query}

    #     ANSWER:
    #     """
    #         # --- STREAM from LLM ---
    #     for chunk in stream_answer(prompt):
    #         yield chunk


    def generate_answer(self, query: str):
       
        # Measure execution time
        start_time = time.time()

        if USE_HYDE:
            hyde_text = self.generate_hyde_query(query)

            # DEBUG
            print("=== ORIGINAL QUERY ===", query)
            print("=== HYDE QUERY ===", hyde_text[:300])

            # embed hypothetical query
            query_embedding = self.embedding_service(hyde_text)
        else:
            query_embedding = self.embedding_service(query)

        # retrieve from chroma
        results = self.chroma_client.query(
            query_embeddings=[query_embedding],
            n_results=3 # or 5
        )

        documents = results["documents"][0]
        # documents = list(dict.fromkeys(documents))  
        # documents = documents[:4]

        # debug
        retrieval_count = len(documents)
        print("=== RETRIEVAL COUNT ===", retrieval_count)


        # remove duplicates
        documents = list(dict.fromkeys(documents))
        
        # re-ranker causing bottleneck, skipping for now
        # # rerank
        # reranked = self.reranker.rerank(query, documents, top_k=2) # uses original user query
        # top_documents = [doc for doc, _ in reranked]

        # # debug
        # rerank_count = len(top_documents)
        # print("=== RERANK COUNT ===", rerank_count)

        # reverse repacking
        reversed_docs = list(reversed(documents)) # top_documents if using reranker

        # compress context
        compressed_docs = self.compress_context(query, reversed_docs) # uses original user query
        
        # build context
        context_blocks = []

        for i, doc in enumerate(compressed_docs):
            context_blocks.append(f"[Source {i+1}]\n{doc}")

        context = "\n\n".join(context_blocks)

        # build prompt uses original user query
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

        # # debug
        # print("=== RAW LLM OUTPUT ===")
        # print(answer)

        # debug
        latency_ms = int((time.time() - start_time) * 1000)
        print("=== RAG LATENCY (ms) ===", latency_ms)

        # clean answer (remove any non-[Source X] citations)
        answer = self.clean_answer(answer)

        # logging metadata 
        metadata = {
            "latency_ms": latency_ms,
            "retrieval_count": retrieval_count,
            # "rerank_count": rerank_count,
            "hyde_used": USE_HYDE,
        }

        return {
            "answer": answer,
            "sources": [
                {"id": i+1, "text": doc}
                for i, doc in enumerate(reversed_docs)
            ],
            "metadata": metadata
        }

    # Context compression by extracting sentences that share keywords with the query
    def compress_context(self, query: str, documents: list[str]) -> list[str]:
        query_words = set(query.lower().split())

        compressed_docs = []

        for doc in documents:
            lines = doc.split("\n")

            relevant_lines = [
                line for line in lines
                if any(word in line.lower() for word in query_words)
            ]

            if relevant_lines:
                compressed_docs.append("\n".join(relevant_lines))
            else:
                compressed_docs.append(doc[:300])  # fallback

        return compressed_docs
    
    # HyDE generator
    def generate_hyde_query(self, query: str) -> str:
            prompt = f"""
        Write a detailed and complete answer to the following question.

        Question:
        {query}

        Answer:
        """

            hyde_response = self.llm_service(prompt)

            return hyde_response.strip()
    
    

    def clean_answer(self, answer: str) -> str:
        # remove any non-[Source X] citations
        answer = re.sub(r"\(.*\)", "", answer)
        # answer = re.sub(r"(?i)according to\s*\[source \d+\],?\s*", "", answer)

        return answer.strip()