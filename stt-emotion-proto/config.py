# STT & Emotion Proto - 설정
# 필요 시 여기서 모델명, 샘플레이트, 청크 길이 등 조정

import os

# Arduino(nano_booth_nav) USB 시리얼 — 감정 분류 후 PLAY:<0-6> 전송
# 끄려면: export ARDUINO_NEO=0
ARDUINO_NEO_ENABLED = os.environ.get("ARDUINO_NEO", "1").lower() not in ("0", "false", "no", "off")
ARDUINO_SERIAL_PORT = os.environ.get("ARDUINO_SERIAL", "/dev/ttyACM0")
ARDUINO_SERIAL_BAUD = 115200

# 라즈베리파이: small/medium은 매우 느림. base 또는 tiny 권장.
WHISPER_MODEL = "base"
EMOTION_MODEL = "j-hartmann/emotion-english-distilroberta-base"

# STT 언어 (Whisper). "en" 고정 시 다국어 오탐·한자 할루시네이션 완화
LANGUAGE = "en"
# Whisper에 영어임을 힌트 (짧게 유지)
WHISPER_INITIAL_PROMPT = "English speech."

# True: /chunk 업로드 시 Whisper 호출 안 함 · 종료 시 한 번만 전사 (Pi 부하 대폭 감소)
SKIP_CHUNK_TRANSCRIPTION = True

SAMPLE_RATE = 16000  # Whisper 권장 16kHz
CHUNK_DURATION_SEC = 3  # 실시간 STT용 청크 길이(초). 이 간격으로 Whisper 호출
