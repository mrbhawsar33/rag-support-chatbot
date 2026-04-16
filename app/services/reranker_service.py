from sentence_transformers import CrossEncoder


class RerankerService:
    def __init__(self):
        self.model = None # stop model loading CrossEncoder("cross-encoder/ms-marco-MiniLM-L6-v2")

    def rerank(self, query: str, documents: list[str], top_k: int = 3):
        pairs = [[query, doc] for doc in documents]

        scores = self.model.predict(pairs)

        scored_docs = list(zip(documents, scores))

        # sort by score (descending)
        ranked = sorted(scored_docs, key=lambda x: x[1], reverse=True)

        # return top_k
        return ranked[:top_k]