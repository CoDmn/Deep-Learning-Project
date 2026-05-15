from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer


class SemanticRetriever:
    def __init__(self, knowledge_base: List[Dict], device: str = None):
        import torch
        _device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        print("Building semantic index...")
        self.kb = knowledge_base
        self.encoder = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2", device=_device
        )
        # pre-encode all documents once so retrieval is fast at inference time
        texts = [item["question"] + " " + item["answer"] for item in knowledge_base]
        self.embeddings = self.encoder.encode(
            texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
        )
        print(f"  Index built over {len(knowledge_base)} documents.")

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        q_emb = self.encoder.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        )[0]
        scores = self.embeddings @ q_emb  # cosine similarity (vectors are normalised)
        top_indices = np.argsort(scores)[-top_k:][::-1]
        return [self.kb[i] for i in top_indices]


BM25Retriever = SemanticRetriever
