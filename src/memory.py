from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class Turn:
    question: str
    rewritten_question: str
    answer: str
    level: str
    confused: bool


@dataclass
class ConversationMemory:
    turns: List[Turn] = field(default_factory=list)
    current_level: str = "normal"
    confusion_streak: int = 0
    clear_streak: int = 0

    def add_turn(self, question: str, rewritten: str, answer: str, confused: bool) -> None:
        self.turns.append(Turn(
            question=question,
            rewritten_question=rewritten,
            answer=answer,
            level=self.current_level,
            confused=confused,
        ))
        self._update_level(question, confused)

    def _update_level(self, question: str, confused: bool) -> None:
        if confused:
            self.confusion_streak += 1
            self.clear_streak = 0
            if self.confusion_streak >= 2:
                self.current_level = "simple"
        else:
            self.clear_streak += 1
            self.confusion_streak = 0
            # go back to normal after 3 clear turns in simple mode
            if self.current_level == "simple" and self.clear_streak >= 3:
                self.current_level = "normal"
            # upgrade to expert if question seems advanced
            elif self.current_level == "normal" and _is_expert_question(question):
                self.current_level = "expert"

    def get_question_history(self) -> List[str]:
        return [t.question for t in self.turns]

    def get_history_text(self, max_turns: int = 4) -> str:
        recent = self.turns[-max_turns:]
        parts = []
        for t in recent:
            parts.append(f"Q: {t.question}")
            parts.append(f"A: {t.answer[:180]}")
        return " | ".join(parts)

    def summary(self) -> Dict:
        return {
            "turns": len(self.turns),
            "current_level": self.current_level,
            "confusion_streak": self.confusion_streak,
            "clear_streak": self.clear_streak,
            "recent_questions": [t.question for t in self.turns[-3:]],
        }

    def reset(self) -> None:
        self.turns.clear()
        self.current_level = "normal"
        self.confusion_streak = 0
        self.clear_streak = 0


# technical keywords used to detect expert-level questions
_EXPERT_SIGNALS = {
    "algorithm", "complexity", "theorem", "proof", "derivative", "gradient",
    "backpropagation", "regularization", "hyperparameter", "architecture",
    "transformer", "attention mechanism", "convolution", "optimization",
    "convergence", "stochastic", "bayesian", "inference", "posterior",
    "entropy", "divergence", "manifold", "embedding", "latent space",
}


def _is_expert_question(question: str) -> bool:
    words = set(question.lower().split())
    return len(words & _EXPERT_SIGNALS) >= 2 or len(question.split()) > 25
