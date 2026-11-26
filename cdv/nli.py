"""NLI used by M1 only for grounding (does this user turn state this condition?).

Model fixed by researcher decision (2026-11-26): MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli (MIT).
Labels are read from id2label. NLI never decides whether a change is legitimate (V-C stays rule-based).
"""
from __future__ import annotations

from functools import lru_cache

MODEL = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"


class NLI:
    def __init__(self, model: str = MODEL):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        self._torch = torch
        self.tok = AutoTokenizer.from_pretrained(model)
        self.model = AutoModelForSequenceClassification.from_pretrained(model).eval()
        lab = {v.lower(): int(k) for k, v in self.model.config.id2label.items()}
        self.ent = lab["entailment"]
        self.calls = 0

    @lru_cache(maxsize=20000)
    def entails(self, premise: str, hypothesis: str) -> bool:
        self.calls += 1
        with self._torch.inference_mode():
            x = self.tok(premise, hypothesis, return_tensors="pt", truncation=True, max_length=512)
            return int(self.model(**x).logits.argmax(-1)) == self.ent
