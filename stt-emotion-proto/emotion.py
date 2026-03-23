"""
Hugging Face emotion classifier (j-hartmann/emotion-english-distilroberta-base).
- 텍스트를 입력받아 하나의 대표 감정 레이블 반환
"""
from typing import List, Tuple

from transformers import pipeline

from config import EMOTION_MODEL

_pipeline = None


def get_pipeline():
    """싱글톤 emotion pipeline 로드."""
    global _pipeline
    if _pipeline is None:
        _pipeline = pipeline("text-classification", model=EMOTION_MODEL, top_k=None)
    return _pipeline


def get_emotion(text: str) -> str:
    """
    텍스트에 대한 하나의 대표 감정 반환.
    """
    if not text or not text.strip():
        return "(no text)"
    pipe = get_pipeline()
    out = pipe(text.strip())
    if not out or not out[0]:
        return ""
    # out[0] is list of {"label": "...", "score": ...}, sort by score descending
    results = out[0] if isinstance(out[0], list) else [out[0]]
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    return results[0]["label"]


def get_emotion_with_scores(text: str) -> List[Tuple[str, float]]:
    """디버깅/UI용: 모든 감정 점수 리스트 반환. [(label, score), ...]"""
    if not text or not text.strip():
        return []
    pipe = get_pipeline()
    out = pipe(text.strip())
    if not out or not out[0]:
        return []
    results = out[0] if isinstance(out[0], list) else [out[0]]
    return [(r["label"], float(r["score"])) for r in sorted(results, key=lambda x: x["score"], reverse=True)]
