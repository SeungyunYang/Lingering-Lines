from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

from audio_stream import start_recording, RecordingSession
from stt_whisper import transcribe, transcribe_chunk, get_model as get_whisper_model
from emotion import get_emotion, get_pipeline as get_emotion_pipeline
from config import SAMPLE_RATE, CHUNK_DURATION_SEC, LANGUAGE


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("STT + Emotion")
        self.root.geometry("520x420")
        self.root.minsize(400, 320)

        self.recording_session: RecordingSession | None = None
        self.transcript_lines = []
        self._models_ready = False

        self._build_ui()
        self._preload_models()

    def _build_ui(self):
        header = ttk.Frame(self.root, padding=(12, 8))
        header.pack(fill=tk.X)
        ttk.Label(header, text="STT + Emotion", font=("", 14, "bold")).pack(anchor=tk.W)
        ttk.Label(header, text="녹음 시작 → 말하기 → 녹음 종료 → 감정 확인", foreground="gray").pack(anchor=tk.W)
        self.status_label = ttk.Label(header, text="Loading models... (first run may take 1–2 min)", foreground="gray")
        self.status_label.pack(anchor=tk.W)

        text_frame = ttk.LabelFrame(self.root, text=" 실시간 텍스트 ", padding=(8, 4))
        text_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        self.text_display = scrolledtext.ScrolledText(text_frame, height=10, wrap=tk.WORD, state=tk.NORMAL)
        self.text_display.pack(fill=tk.BOTH, expand=True)

        emotion_frame = ttk.Frame(self.root, padding=(12, 4))
        emotion_frame.pack(fill=tk.X)
        ttk.Label(emotion_frame, text="대표 감정:").pack(side=tk.LEFT, padx=(0, 6))
        self.emotion_label = ttk.Label(emotion_frame, text="—", font=("", 12, "bold"))
        self.emotion_label.pack(side=tk.LEFT)

        btn_frame = ttk.Frame(self.root, padding=(12, 8))
        btn_frame.pack(fill=tk.X)
        self.btn_start = ttk.Button(btn_frame, text="녹음 시작", command=self._on_start, state=tk.DISABLED)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_stop = ttk.Button(btn_frame, text="녹음 종료", command=self._on_stop, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="감정 분석", command=self._on_emotion).pack(side=tk.LEFT)

    def _preload_models(self):
        """창이 뜬 뒤 백그라운드에서 Whisper·감정 모델 로드. 완료 시 버튼 활성화."""
        def load():
            try:
                get_whisper_model()
                get_emotion_pipeline()
                self.root.after(0, self._on_models_ready)
            except Exception as e:
                self.root.after(0, lambda: self._on_models_failed(str(e)))

        threading.Thread(target=load, daemon=True).start()

    def _on_models_ready(self):
        self._models_ready = True
        self.status_label.config(text="Ready")
        self.btn_start.config(state=tk.NORMAL)

    def _on_models_failed(self, err: str):
        self.status_label.config(text=f"Model load failed: {err}")
        self.btn_start.config(state=tk.NORMAL)

    def _on_start(self):
        self.transcript_lines = []
        self.text_display.delete(1.0, tk.END)
        self.emotion_label.config(text="—")
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        self.recording_session = start_recording(
            on_chunk=self._on_audio_chunk,
            sample_rate=SAMPLE_RATE,
            chunk_seconds=CHUNK_DURATION_SEC,
        )

    def _on_audio_chunk(self, audio_chunk):
        """녹음 스레드에서 호출됨. 별도 스레드에서 STT 후 메인 스레드로 화면 갱신."""
        def process():
            try:
                text = transcribe_chunk(audio_chunk, language=LANGUAGE)
                if text:
                    self.root.after(0, lambda t=text: self._append_transcript(t))
            except Exception:
                pass

        threading.Thread(target=process, daemon=True).start()

    def _append_transcript(self, text: str):
        if not text:
            return
        self.transcript_lines.append(text)
        self.text_display.insert(tk.END, text + " ")
        self.text_display.see(tk.END)

    def _on_stop(self):
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

        session = self.recording_session
        self.recording_session = None

        def do_stop():
            if session:
                session.stop()
                full_audio = session.get_audio()
            else:
                full_audio = None

            full_text = self.text_display.get(1.0, tk.END).strip()
            if not full_text and full_audio is not None and full_audio.size > 0:
                try:
                    full_text = transcribe(full_audio, language=LANGUAGE)
                    self.root.after(0, lambda: self._set_full_text(full_text))
                except Exception:
                    pass

            if full_text:
                try:
                    emotion = get_emotion(full_text)
                    self.root.after(0, lambda e=emotion: self.emotion_label.config(text=e))
                except Exception as ex:
                    self.root.after(0, lambda: self.emotion_label.config(text=f"(오류: {ex})"))
            else:
                self.root.after(0, lambda: self.emotion_label.config(text="(텍스트 없음)"))

        threading.Thread(target=do_stop, daemon=True).start()

    def _set_full_text(self, text: str):
        if not text:
            return
        self.text_display.delete(1.0, tk.END)
        self.text_display.insert(tk.END, text)

    def _on_emotion(self):
        full_text = self.text_display.get(1.0, tk.END).strip()
        if not full_text:
            messagebox.showinfo("안내", "먼저 녹음 후 텍스트가 있거나, 텍스트를 입력해 주세요.")
            return

        def run():
            try:
                e = get_emotion(full_text)
                self.root.after(0, lambda em=e: self.emotion_label.config(text=em))
            except Exception as ex:
                self.root.after(0, lambda: self.emotion_label.config(text=f"(오류: {ex})"))

        threading.Thread(target=run, daemon=True).start()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
