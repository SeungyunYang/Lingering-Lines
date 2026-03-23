# STT & Emotion Proto - 설정
# 필요 시 여기서 모델명, 샘플레이트, 청크 길이 등 조정

WHISPER_MODEL = "base"  # "tiny", "base", "small", "medium", "large" 등
EMOTION_MODEL = "j-hartmann/emotion-english-distilroberta-base"

# STT 언어 (Whisper). "en" = 영어만
LANGUAGE = "en"

SAMPLE_RATE = 16000  # Whisper 권장 16kHz
CHUNK_DURATION_SEC = 3  # 실시간 STT용 청크 길이(초). 이 간격으로 Whisper 호출
