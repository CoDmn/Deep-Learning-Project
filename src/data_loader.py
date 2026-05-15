import os
import json
from typing import List, Dict

CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "qrecc_kb.json")


def load_qrecc_knowledge_base(max_items: int = 5000) -> List[Dict]:
    # Load from cache if already downloaded
    if os.path.exists(CACHE_PATH):
        print("Loading KB from local cache...")
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            kb = json.load(f)
        print(f"  {len(kb)} items loaded.")
        return kb

    print("Downloading QReCC dataset...")
    from datasets import load_dataset

    try:
        dataset = load_dataset("castorini/qrecc", split="train")
    except Exception:
        dataset = load_dataset("voidful/QReCC", split="train")

    # field names vary slightly depending on which version of the dataset
    first = dataset[0]
    q_key = _pick_key(first, ["Truth_rewrite", "Rewrite", "rewrite", "Question", "question"])
    a_key = _pick_key(first, ["Answer", "answer"])

    kb = []
    for i, item in enumerate(dataset):
        if i >= max_items:
            break
        question = (item.get(q_key) or "").strip()
        answer = (item.get(a_key) or "").strip()
        if question and answer and len(answer) > 30:
            kb.append({"id": i, "question": question, "answer": answer})

    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False)

    print(f"  {len(kb)} items saved to cache.")
    return kb


def _pick_key(item: dict, candidates: List[str]) -> str:
    for k in candidates:
        if k in item and item[k]:
            return k
    return candidates[-1]
