"""
마이크 녹음 스트림 처리.
- 녹음 시작/중지
- 실시간 갱신을 위해 N초 단위 청크 콜백 지원
- 녹음된 전체 오디오 반환 (numpy)
"""
import threading
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from config import SAMPLE_RATE, CHUNK_DURATION_SEC


def start_recording(
    on_chunk: Optional[Callable] = None,
    *,
    sample_rate: int = SAMPLE_RATE,
    chunk_seconds: float = CHUNK_DURATION_SEC,
) -> "RecordingSession":
    """
    녹음 시작.
    on_chunk: 청크가 찼을 때 호출되는 콜백 (실시간 STT용). None이면 청크 콜백 없음.
    RecordingSession 인스턴스를 반환. stop() 호출 시 녹음 중지 및 전체 오디오 반환.
    """
    session = RecordingSession(on_chunk=on_chunk, sample_rate=sample_rate, chunk_seconds=chunk_seconds)
    session._start()
    return session


def get_default_input_device() -> Optional[int]:
    """기본 입력(마이크) 디바이스 인덱스. None이면 시스템 기본."""
    return None


class RecordingSession:
    """녹음 세션. stop() 호출 시 녹음 중지하고 get_audio()로 데이터 반환."""

    def __init__(self, on_chunk: Optional[Callable] = None, sample_rate: int = 16000, chunk_seconds: float = 3.0):
        self._running = True
        self._audio_chunks = []
        self._on_chunk = on_chunk
        self._sample_rate = sample_rate
        self._chunk_samples = int(chunk_seconds * sample_rate)
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    def _start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        buffer = np.array([], dtype=np.float32)
        block_size = 1024

        with sd.InputStream(samplerate=self._sample_rate, channels=1, dtype="float32", blocksize=block_size) as stream:
            while self._running:
                try:
                    chunk, _ = stream.read(block_size)
                except Exception:
                    break
                if not self._running or chunk is None:
                    break
                buffer = np.concatenate([buffer, chunk.ravel()]) if buffer.size else chunk.ravel()

                while buffer.size >= self._chunk_samples and self._running:
                    piece = buffer[: self._chunk_samples].copy()
                    buffer = buffer[self._chunk_samples :]
                    with self._lock:
                        self._audio_chunks.append(piece)
                    if self._on_chunk:
                        try:
                            self._on_chunk(piece)
                        except Exception:
                            pass

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def get_audio(self) -> np.ndarray:
        """녹음된 전체 오디오 (float32 mono)."""
        with self._lock:
            if not self._audio_chunks:
                return np.array([], dtype=np.float32)
            return np.concatenate(self._audio_chunks)

    @property
    def is_running(self) -> bool:
        return self._running
