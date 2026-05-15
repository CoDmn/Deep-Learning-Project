from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer

# phrases that explicitly signal the student is confused
_CONFUSION_PHRASES = [
    "i don't understand", "i dont understand", "i do not understand",
    "i don't get it", "i dont get it",
    "what do you mean", "can you explain", "explain again",
    "i'm confused", "im confused", "i am confused",
    "not clear", "unclear", "can you clarify", "still don't understand",
    "still dont", "huh", "what?", "i'm lost", "im lost",
]

# similarity threshold above which we consider the question a repetition
_SIMILARITY_THRESHOLD = 0.82


class ConfusionDetector:
    def __init__(self, device: str = None):
        import torch
        _device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        print("Loading confusion detector...")
        self.encoder = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2", device=_device
        )

    def detect(self, current_question: str, question_history: List[str]) -> Dict:
        # check for explicit confusion phrases first
        q_lower = current_question.lower()
        for phrase in _CONFUSION_PHRASES:
            if phrase in q_lower:
                return {"confused": True, "reason": "explicit_phrase", "similarity": 1.0}

        # check semantic similarity with recent questions
        if question_history:
            recent = question_history[-3:]
            all_texts = recent + [current_question]
            embeddings = self.encoder.encode(
                all_texts, convert_to_numpy=True, normalize_embeddings=True
            )
            current_emb = embeddings[-1]
            prev_embs = embeddings[:-1]
            similarities = prev_embs @ current_emb
            max_sim = float(similarities.max())

            if max_sim >= _SIMILARITY_THRESHOLD:
                return {
                    "confused": True,
                    "reason": "semantic_repetition",
                    "similarity": round(max_sim, 3),
                }
            return {"confused": False, "reason": "none", "similarity": round(max_sim, 3)}

        return {"confused": False, "reason": "none", "similarity": 0.0}
