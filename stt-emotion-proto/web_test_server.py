from __future__ import annotations

import os
import socket
import tempfile
import threading
import uuid
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import sounddevice as sd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel

from arduino_neo import notify_arduino_emotion
from config import (
    ARDUINO_NEO_ENABLED,
    ARDUINO_SERIAL_PORT,
    LANGUAGE,
    SKIP_CHUNK_TRANSCRIPTION,
    WHISPER_INITIAL_PROMPT,
)
from stt_whisper import get_model as get_whisper_model


EMOTION_LABELS = ["joy", "sadness", "anger", "fear", "love", "disgust", "neutral"]
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
WEB_DIR = Path(__file__).resolve().parent / "web"


@dataclass
class SessionState:
    transcript_parts: list[str] = field(default_factory=list)
    live_text: str = ""
    lock: threading.Lock = field(default_factory=threading.Lock)
    server_record_stop: threading.Event | None = None
    server_record_thread: threading.Thread | None = None
    server_chunks: list[np.ndarray] = field(default_factory=list)
    server_sr: int = 0


class ServerRecordStartIn(BaseModel):
    """비우면 장치 이름에 'lavalier'가 들어간 입력을 우선 선택."""

    device_index: int | None = None


app = FastAPI(title="Whisper STT Web Test")
app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")

_sessions: dict[str, SessionState] = {}
_sessions_lock = threading.Lock()
_whisper_lock = threading.Lock()
_openai_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        import httpx

        _openai_client = OpenAI(timeout=httpx.Timeout(60.0, connect=15.0))
    return _openai_client


def list_input_devices() -> list[dict[str, Any]]:
    devices = sd.query_devices()
    out: list[dict[str, Any]] = []
    for idx, dev in enumerate(devices):
        if int(dev.get("max_input_channels", 0)) <= 0:
            continue
        out.append(
            {
                "index": idx,
                "name": dev.get("name", ""),
                "max_input_channels": int(dev.get("max_input_channels", 0)),
                "default_samplerate": float(dev.get("default_samplerate", 0)),
            }
        )
    return out


def resolve_server_mic(device_index: int | None) -> tuple[int, float]:
    devices = list_input_devices()
    if not devices:
        raise HTTPException(status_code=400, detail="입력 장치가 없습니다.")
    if device_index is not None:
        for d in devices:
            if int(d["index"]) == int(device_index):
                return int(d["index"]), float(d["default_samplerate"])
        raise HTTPException(status_code=400, detail=f"device_index={device_index} 를 찾을 수 없습니다.")
    for d in devices:
        if "lavalier" in str(d.get("name", "")).lower():
            return int(d["index"]), float(d["default_samplerate"])
    d0 = devices[0]
    return int(d0["index"]), float(d0["default_samplerate"])


def write_temp_wav_mono_f32(samples: np.ndarray, sr: int) -> str:
    x = np.clip(samples.astype(np.float64, copy=False), -1.0, 1.0)
    pcm = (x * 32767.0).astype(np.int16)
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr))
        wf.writeframes(pcm.tobytes())
    return path


def server_record_worker(session_id: str, device: int, sr: float) -> None:
    # 전사는 하지 않고 버퍼만 쌓음 — 짧은 블록(정지 반응)과 오버헤드 균형
    chunk_s = 2.0
    frames = max(1, int(chunk_s * sr))
    while True:
        with _sessions_lock:
            st = _sessions.get(session_id)
        if st is None or st.server_record_stop is None:
            return
        if st.server_record_stop.is_set():
            return
        try:
            block = sd.rec(frames, samplerate=sr, channels=1, dtype="float32", device=device)
            sd.wait()
        except Exception:
            return
        if st.server_record_stop.is_set():
            return
        flat = np.asarray(block, dtype=np.float32).reshape(-1)
        with st.lock:
            st.server_chunks.append(flat.copy())
            # 녹음 중 Whisper 호출 없음 — Pi에서 청크마다 전사하면 수십 배 느려짐. 종료 시 1회만 전사.
            st.live_text = ""


def classify_emotion_with_openai(text: str) -> str:
    client = get_openai_client()
    labels = ", ".join(EMOTION_LABELS)
    prompt = (
        "You are an emotion classifier. "
        f"Choose exactly one label from: {labels}. "
        "Return only the label in lowercase."
    )
    res = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
    )
    raw = (res.output_text or "").strip().lower()
    if raw in EMOTION_LABELS:
        return raw
    # fallback: label 포함 여부로 보정
    for label in EMOTION_LABELS:
        if label in raw:
            return label
    return "neutral"


def transcribe_file(path: str) -> str:
    # Whisper 모델은 thread-safe 보장이 없어 단일 lock으로 호출
    kw: dict = {"fp16": False, "verbose": False, "task": "transcribe"}
    if LANGUAGE:
        kw["language"] = LANGUAGE
    if WHISPER_INITIAL_PROMPT:
        kw["initial_prompt"] = WHISPER_INITIAL_PROMPT
    with _whisper_lock:
        model = get_whisper_model()
        result = model.transcribe(path, **kw)
    return (result.get("text") or "").strip()


@app.get("/")
def root() -> FileResponse:
    return FileResponse(str(WEB_DIR / "index.html"))


@app.get("/api/server-info")
def server_info() -> dict[str, Any]:
    return {
        "ok": True,
        "hostname": socket.gethostname(),
        "arduino_neo_enabled": ARDUINO_NEO_ENABLED,
        "arduino_serial": ARDUINO_SERIAL_PORT,
    }


@app.get("/api/mic/devices")
def mic_devices() -> dict[str, Any]:
    try:
        devices = list_input_devices()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"마이크 장치 조회 실패: {exc}") from exc
    return {"ok": True, "devices": devices, "count": len(devices)}


@app.post("/api/session/start")
def session_start() -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    with _sessions_lock:
        _sessions[session_id] = SessionState()
    return {"ok": True, "session_id": session_id}


@app.get("/api/session/{session_id}/live")
def session_live(session_id: str) -> dict[str, Any]:
    with _sessions_lock:
        st = _sessions.get(session_id)
    if st is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    with st.lock:
        return {"ok": True, "full_text": st.live_text}


@app.post("/api/session/{session_id}/server-record/start")
def server_record_start(session_id: str, body: ServerRecordStartIn = ServerRecordStartIn()) -> dict[str, Any]:
    with _sessions_lock:
        st = _sessions.get(session_id)
    if st is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    if st.server_record_thread is not None and st.server_record_thread.is_alive():
        raise HTTPException(status_code=409, detail="이미 서버 녹음 중입니다.")

    req_index = body.device_index
    device, sr = resolve_server_mic(req_index)
    st.server_chunks = []
    st.server_sr = int(sr)
    st.server_record_stop = threading.Event()
    st.server_record_thread = threading.Thread(
        target=server_record_worker,
        args=(session_id, device, float(sr)),
        daemon=True,
    )
    st.server_record_thread.start()
    dev_name = ""
    for d in list_input_devices():
        if int(d["index"]) == device:
            dev_name = str(d.get("name", ""))
            break
    return {"ok": True, "device_index": device, "samplerate": sr, "device_name": dev_name}


@app.post("/api/session/{session_id}/server-record/finish")
def server_record_finish(session_id: str) -> dict[str, Any]:
    with _sessions_lock:
        st = _sessions.get(session_id)
    if st is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    if st.server_record_thread is None:
        raise HTTPException(status_code=400, detail="서버 녹음이 시작되지 않았습니다.")

    if st.server_record_stop is not None:
        st.server_record_stop.set()
    st.server_record_thread.join(timeout=300.0)
    st.server_record_thread = None
    st.server_record_stop = None

    with st.lock:
        chunks = list(st.server_chunks)
        sr = int(st.server_sr)
        full_text = st.live_text

    with _sessions_lock:
        _sessions.pop(session_id, None)

    if chunks:
        audio = np.concatenate(chunks)
        path = write_temp_wav_mono_f32(audio, sr)
        try:
            text_from_full = transcribe_file(path)
            if text_from_full:
                full_text = text_from_full
        except Exception:
            pass
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    emotion = "(text-empty)"
    if full_text:
        try:
            emotion = classify_emotion_with_openai(full_text)
        except Exception as exc:
            emotion = f"(emotion-error: {exc})"

    neo = notify_arduino_emotion(emotion, EMOTION_LABELS)
    return {"ok": True, "text": full_text, "emotion": emotion, **neo}


@app.post("/api/session/{session_id}/chunk")
async def session_chunk(session_id: str, audio: UploadFile = File(...)) -> dict[str, Any]:
    with _sessions_lock:
        st = _sessions.get(session_id)
    if st is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    suffix = Path(audio.filename or "chunk.webm").suffix or ".webm"
    content = await audio.read()
    if not content:
        return {"ok": True, "text": "", "full_text": " ".join(st.transcript_parts).strip()}

    if SKIP_CHUNK_TRANSCRIPTION:
        with st.lock:
            full_text = st.live_text
        return {"ok": True, "text": "", "full_text": full_text, "chunk_error": ""}

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        temp_path = tmp.name

    try:
        text = transcribe_file(temp_path)
        chunk_error = ""
    except Exception as exc:
        # MediaRecorder 조각(webm) 중 일부는 단독 디코딩이 실패할 수 있음.
        # 실시간 표시용 청크는 실패 시 건너뛰고, 종료 시 전체 오디오로 최종 STT를 수행.
        text = ""
        chunk_error = str(exc)
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

    with st.lock:
        if text:
            # 실시간 chunk는 "누적 오디오"를 받아오므로 현재 시점의 전체 텍스트로 간주
            st.live_text = text
        full_text = st.live_text

    return {"ok": True, "text": text, "full_text": full_text, "chunk_error": chunk_error}


@app.post("/api/session/{session_id}/finish")
async def session_finish(session_id: str, audio: UploadFile | None = File(default=None)) -> dict[str, Any]:
    with _sessions_lock:
        st = _sessions.pop(session_id, None)
    if st is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    with st.lock:
        full_text = st.live_text or " ".join(st.transcript_parts).strip()

    # 가능하면 종료 시 전체 오디오를 우선 STT (청크 누락/디코딩 실패 보정)
    if audio is not None:
        suffix = Path(audio.filename or "final.webm").suffix or ".webm"
        content = await audio.read()
        if content:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(content)
                temp_path = tmp.name
            try:
                text_from_full = transcribe_file(temp_path)
                if text_from_full:
                    full_text = text_from_full
            except Exception:
                # 전체 파일 디코딩 실패 시에도 기존 청크 텍스트로 계속 진행
                pass
            finally:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    emotion = "(text-empty)"
    if full_text:
        try:
            emotion = classify_emotion_with_openai(full_text)
        except Exception as exc:
            emotion = f"(emotion-error: {exc})"

    neo = notify_arduino_emotion(emotion, EMOTION_LABELS)
    return {"ok": True, "text": full_text, "emotion": emotion, **neo}
