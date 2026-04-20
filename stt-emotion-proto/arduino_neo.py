"""
라즈베리파이 USB 시리얼 → Arduino (nano_booth_nav.ino)
감정 분류 후 기존 프로토콜: PLAY:<0-6>\\n  (0=joy … 6=neutral, EMOTION_SEGS 순서 동일)
"""
from __future__ import annotations

import threading
from typing import Any

try:
    import serial
except ImportError:
    serial = None  # type: ignore[misc, assignment]

from config import ARDUINO_NEO_ENABLED, ARDUINO_SERIAL_BAUD, ARDUINO_SERIAL_PORT

_serial: Any = None
_lock = threading.Lock()


def _connection() -> Any:
    global _serial
    if serial is None:
        raise RuntimeError("pyserial 미설치 (pip install pyserial)")
    with _lock:
        if _serial is not None and _serial.is_open:
            return _serial
        _serial = serial.Serial(
            ARDUINO_SERIAL_PORT,
            ARDUINO_SERIAL_BAUD,
            timeout=0.2,
            write_timeout=0.5,
        )
        return _serial


def send_play_emotion(index: int) -> None:
    if index < 0 or index > 6:
        index = 6
    ser = _connection()
    ser.write(f"PLAY:{index}\n".encode("ascii", errors="replace"))
    ser.flush()


def notify_arduino_emotion(emotion: str, valid_labels: list[str]) -> dict[str, Any]:
    """
    OpenAI 분류 결과가 valid_labels 중 하나일 때만 PLAY:n 전송.
    (오류 문자열·빈 텍스트 등은 전송하지 않음)
    """
    low = (emotion or "").strip().lower()
    if low not in valid_labels:
        return {
            "neo_ok": False,
            "neo_index": None,
            "neo_message": "7감정 라벨이 아니어 Arduino 전송 생략",
        }
    idx = valid_labels.index(low)
    if not ARDUINO_NEO_ENABLED:
        return {
            "neo_ok": False,
            "neo_index": idx,
            "neo_message": "ARDUINO_NEO=0 으로 비활성",
        }
    if serial is None:
        return {
            "neo_ok": False,
            "neo_index": idx,
            "neo_message": "pyserial 미설치",
        }
    try:
        send_play_emotion(idx)
        return {"neo_ok": True, "neo_index": idx, "neo_message": "ok"}
    except Exception as exc:
        return {
            "neo_ok": False,
            "neo_index": idx,
            "neo_message": f"{type(exc).__name__}: {exc}",
        }
