import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from typing import List

MODEL_NAME = "google/flan-t5-base"

# prompts that control how the model answers depending on the student level
_LEVEL_INSTRUCTIONS = {
    "simple": (
        "You are a patient tutor explaining to a complete beginner. "
        "Use very simple words, short sentences, and a concrete example."
    ),
    "normal": (
        "You are a helpful tutor. Give a clear, well-structured answer."
    ),
    "expert": (
        "You are an expert tutor. Provide a thorough, technically precise answer "
        "with relevant depth and nuance."
    ),
}


class ModelBackend:
    def __init__(self, device: str = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Loading {MODEL_NAME} on {self.device} ...")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(self.device)
        self.model.eval()
        print("Model ready.")

    def rewrite_question(self, question_history: List[str], current_question: str) -> str:
        if not question_history:
            return current_question

        history_text = " | ".join(question_history[-4:])
        prompt = (
            "Rewrite the following question so it is fully self-contained and clear, "
            "resolving any pronouns or references using the conversation history. "
            "Output only the rewritten question, nothing else.\n\n"
            f"Conversation history: {history_text}\n"
            f"Current question: {current_question}\n"
            "Rewritten question:"
        )
        return self._generate(prompt, max_new_tokens=80)

    def generate_answer(self, question: str, context: str, level: str = "normal") -> str:
        instruction = _LEVEL_INSTRUCTIONS.get(level, _LEVEL_INSTRUCTIONS["normal"])
        ctx_section = f"\nContext: {context[:500]}" if context else ""
        prompt = (
            f"{instruction}\n"
            f"Question: {question}"
            f"{ctx_section}\n"
            "Answer:"
        )
        return self._generate(prompt, max_new_tokens=220)

    def _generate(self, prompt: str, max_new_tokens: int = 200) -> str:
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            max_length=768,
            truncation=True,
        ).to(self.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                no_repeat_ngram_size=4,
                repetition_penalty=1.3,
            )

        return self.tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()
