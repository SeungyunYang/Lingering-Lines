# Whisper 웹 테스트 (마이크 + 실시간 STT + 7감정)

## 1) 설치

```bash
cd ~/Lingering-Lines/stt-emotion-proto
source ~/Lingering-Lines/.venv/bin/activate
pip install -r requirements.txt
```

## 2) OpenAI 키 설정

종료 후 감정 분류에 OpenAI API를 사용합니다.

```bash
export OPENAI_API_KEY="your_key_here"
# 선택: 모델 변경
# export OPENAI_MODEL="gpt-4o-mini"
```

## 3) 서버 실행

```bash
cd ~/Lingering-Lines/stt-emotion-proto
source ~/Lingering-Lines/.venv/bin/activate
uvicorn web_test_server:app --host 0.0.0.0 --port 8010 --reload
```

브라우저에서:

- 같은 라즈베리파이에서 열기: `http://localhost:8010`
- 다른 기기에서 열기: `http://<라즈베리파이IP>:8010`

## 4) 테스트 순서

1. **브라우저 마이크 권한 테스트**
2. **라즈베리파이 입력 장치 조회** (USB 마이크 인식 확인)
3. **녹음 시작** 클릭 후 말하기 (청크 단위로 STT 표시)
4. **녹음 종료 + 감정 분류** 클릭
5. 하단에 7감정 중 하나 출력 (`joy/sadness/anger/fear/love/disgust/neutral`)

## 참고

- 실시간 표시는 엄밀한 스트리밍이 아니라 **1.2초 청크 업로드 기반 준실시간**입니다.
- Whisper가 `webm` 디코딩에 `ffmpeg`를 사용하므로, 시스템에 ffmpeg가 필요합니다.
