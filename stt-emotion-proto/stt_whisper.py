"""
Whisper 기반 STT.
- 오디오(numpy 배열)를 받아 텍스트 반환
- 실시간용: 짧은 청크별로 호출 가능
"""
from typing import Union

import numpy as np
import whisper

from config import LANGUAGE, WHISPER_INITIAL_PROMPT, WHISPER_MODEL

_model = None


def get_model():
    """싱글톤 Whisper 모델 로드."""
    global _model
    if _model is None:
        _model = whisper.load_model(WHISPER_MODEL)
    return _model


def transcribe(audio: Union[bytes, np.ndarray], *, language: str = LANGUAGE) -> str:
    """
    오디오를 텍스트로 변환.
    audio: 16kHz mono (float32 numpy array 또는 bytes)
    language: config.LANGUAGE 사용 (기본 "en").
    """
    if audio is None or (isinstance(audio, np.ndarray) and audio.size == 0):
        return ""
    if isinstance(audio, bytes):
        audio = np.frombuffer(audio, dtype=np.float32)
    if audio.dtype != np.float32:
        audio = audio.astype(np.float32) / (np.iinfo(audio.dtype).max + 1)

    # Whisper 최소 길이 대략 0.5초 이상 권장; 너무 짧으면 빈 문자열 반환
    if audio.size < 8000:
        return ""

    model = get_model()
    kw: dict = {"fp16": False, "verbose": False, "task": "transcribe"}
    if language:
        kw["language"] = language
    if WHISPER_INITIAL_PROMPT:
        kw["initial_prompt"] = WHISPER_INITIAL_PROMPT
    result = model.transcribe(audio, **kw)
    text = (result.get("text") or "").strip()
    return text


def transcribe_chunk(audio_chunk: Union[bytes, np.ndarray], language: str = LANGUAGE) -> str:
    """짧은 청크용 (실시간 STT). transcribe와 동일 인터페이스."""
    return transcribe(audio_chunk, language=language)
