from typing import Tuple, Dict, List
import re
import torch

from .data_loader import load_qrecc_knowledge_base
from .retriever import BM25Retriever
from .model_backend import ModelBackend
from .memory import ConversationMemory
from .confusion import ConfusionDetector


# pronouns that indicate the question depends on previous context
_PRONOUNS = {
    "it", "its", "this", "that", "these", "those", "they", "them",
    "he", "she", "his", "her", "we", "our", "such",
}


def _needs_rewriting(question: str) -> bool:
    words = set(question.lower().split())
    return bool(words & _PRONOUNS)


def _first_n_sentences(text: str, n: int) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return " ".join(sentences[:n])


def _adapt_answer(retrieved: List[Dict], level: str) -> str:
    if not retrieved:
        return "I couldn't find information about that. Could you rephrase your question?"

    best = retrieved[0]["answer"]

    if level == "simple":
        core = _first_n_sentences(best, 2)
        return f"Here's a simple explanation: {core}"
    elif level == "expert" and len(retrieved) >= 2:
        second = retrieved[1]["answer"]
        return f"{best}\n\nAdditionally: {_first_n_sentences(second, 3)}"
    else:
        return best


class ConvoTutor:
    def __init__(self, max_kb_items: int = 5000):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"\n=== Initialising ConvoTutor (device: {device}) ===")

        kb = load_qrecc_knowledge_base(max_kb_items)
        self.retriever = BM25Retriever(kb)
        self.model = ModelBackend(device=device)
        self.confusion_detector = ConfusionDetector(device=device)
        self.memory = ConversationMemory()

        print("=== ConvoTutor ready ===\n")

    def chat(self, user_question: str) -> Tuple[str, Dict]:
        question_history = self.memory.get_question_history()

        # detect confusion on the raw question before any rewriting
        confusion = self.confusion_detector.detect(user_question, question_history)
        if confusion["confused"] and self.memory.current_level != "simple":
            self.memory.current_level = "simple"

        # rewrite only when the question has context-dependent references
        if confusion["confused"] and question_history:
            # re-use the last real question so we search for the same topic
            rewritten = question_history[-1]
        elif _needs_rewriting(user_question) and question_history:
            rewritten = self.model.rewrite_question(question_history, user_question)
        else:
            rewritten = user_question

        # retrieve relevant passages and build a level-appropriate answer
        retrieved = self.retriever.retrieve(rewritten, top_k=3)
        answer = _adapt_answer(retrieved, self.memory.current_level)

        self.memory.add_turn(
            question=user_question,
            rewritten=rewritten,
            answer=answer,
            confused=confusion["confused"],
        )

        metadata = {
            "rewritten_question": rewritten,
            "level": self.memory.current_level,
            "confused": confusion["confused"],
            "confusion_reason": confusion["reason"],
            "confusion_similarity": confusion["similarity"],
            "retrieved_count": len(retrieved),
            "retrieved_snippets": [r["answer"][:120] for r in retrieved],
            "memory": self.memory.summary(),
        }

        return answer, metadata

    def reset(self) -> None:
        self.memory.reset()
