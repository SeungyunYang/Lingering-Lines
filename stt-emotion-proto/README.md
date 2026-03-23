# STT + Emotion Proto

Whisper STT와 Hugging Face 감정 분류기를 이용한 프로토타입입니다.

- **녹음 시작** → 마이크로 말하기 → 화면에 실시간(청크 단위)으로 텍스트 표시  
- **녹음 종료** → 전체 텍스트를 `j-hartmann/emotion-english-distilroberta-base`로 분석 → **대표 감정** 표시

## 파일 구조

```
stt-emotion-proto/
  app.py           # 메인 GUI (녹음/종료 버튼, 실시간 텍스트, 감정 표시)
  audio_stream.py  # 마이크 녹음 시작·중지, 청크 콜백(실시간 STT용)
  stt_whisper.py   # Whisper 로드 및 오디오 → 텍스트
  emotion.py       # HF emotion classifier, 텍스트 → 대표 감정
  config.py        # 모델명, 샘플레이트, 청크 길이 등
  requirements.txt
  README.md
```

## 역할 정리

| 파일 | 역할 |
|------|------|
| `app.py` | tkinter GUI. 녹음 시작/종료/감정 분석 버튼, 실시간 텍스트 영역, 대표 감정 라벨. 백그라운드 스레드에서 STT/감정 호출 후 `root.after`로 UI 갱신 |
| `audio_stream.py` | `start_recording(on_chunk=...)`로 녹음 시작, N초마다 `on_chunk(audio_chunk)` 호출. `RecordingSession.stop()` / `get_audio()` 로 전체 오디오 반환 |
| `stt_whisper.py` | `transcribe(audio)` (전체), `transcribe_chunk(audio_chunk)` (실시간용). 16kHz mono 가정 |
| `emotion.py` | `get_emotion(text)` → 대표 감정 문자열 하나 반환 |
| `config.py` | `WHISPER_MODEL`, `EMOTION_MODEL`, `SAMPLE_RATE`, `CHUNK_DURATION_SEC` |

## 실행 방법

1. **macOS에서 tkinter 오류가 나는 경우** (예: `macOS 26 or later required`):  
   Homebrew Python을 사용합니다. 이 프로젝트는 `.vscode/settings.json`에서 `python.defaultInterpreterPath`를 Homebrew 경로로 두었으므로, Cursor에서 **재생 버튼** 또는 **Run > Start Debugging**으로 실행하면 됩니다.  
   Homebrew Python이 없다면: `brew install python-tk`  
   터미널에서 실행: `./run.sh` (Apple Silicon은 `/opt/homebrew/bin/python3`, Intel Mac은 `/usr/local/bin/python3` 사용)

2. 가상환경 생성 및 활성화 후 의존성 설치:
   ```bash
   cd stt-emotion-proto
   pip install -r requirements.txt
   ```
3. PyTorch는 [공식 안내](https://pytorch.org/get-started/locally/)에 따라 환경에 맞게 설치 권장.
4. GUI 실행:
   ```bash
   python app.py
   ```
   또는 Cursor에서 `app.py` 열고 **재생 버튼** 또는 **F5** (Launch: "STT+Emotion (Homebrew Python)" 선택).

현재 `app.py` / `audio_stream.py` / `stt_whisper.py` / `emotion.py`는 **뼈대만** 있어서, 각 모듈의 `TODO`를 구현하면 동작합니다.

## 실시간 텍스트 흐름

- `start_recording(on_chunk=...)` 에서 `CHUNK_DURATION_SEC`(예: 3초)마다 청크를 넘김.
- `on_chunk` 안에서 `transcribe_chunk(audio_chunk)` 호출 → 반환된 문장을 GUI에 누적 표시 (다른 스레드이므로 `root.after(0, ...)` 로 메인 스레드에서 갱신).
- 녹음 종료 시 `get_audio()`로 전체 오디오를 한 번 더 `transcribe()` 해서 최종 문장 보정하거나, 청크 결과만 이어 붙여서 사용할 수 있음.

## UI 개선

기본은 표준 `tkinter`입니다. 더 깔끔한 UI를 원하면 `customtkinter`를 설치한 뒤 `app.py`에서 `tkinter` 대신 `customtkinter`로 위젯을 교체하면 됩니다.
