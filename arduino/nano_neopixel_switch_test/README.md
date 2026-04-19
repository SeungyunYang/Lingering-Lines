# NeoPixel + 스위치 테스트 (Back / Select / Next)

## 동작

| 스위치 | 핀 | 동작 |
|--------|-----|------|
| Back | D2 | 감정 **이전** (0←6 순환) |
| Select | D3 | 전체 NeoPixel **끄기 / 켜기** 토글 |
| Next | D5 | 감정 **다음** (0→6 순환) |

- `INPUT_PULLUP` — 누르면 LOW, 안 누르면 HIGH.
- 감정 0~6 색 패턴은 `nano_neopixel_emotion_test.ino` 와 동일하게 맞춰 둠 (수정 시 **두 파일 모두** 동기화 권장).
- **USB 시리얼 115200**: 감정/LED 상태를 한 줄씩 출력 → 라즈베리파이에서 `rpi-eink-test/emotion_serial_eink.py` 로 e-ink 에 동시 표시 가능.

시리얼 형식:

- `EMO:0` … `EMO:6` — Back/Next 로 감정이 바뀔 때
- `LED:0` — Select 로 NeoPixel 전체 끔
- `LED:1` — Select 로 NeoPixel 켬

부팅 직후 한 번 `EMO:` / `LED:` 가 연속 출력됨.

## 라즈베리파이에서 업로드

```bash
cd ~/Lingering-Lines/arduino/nano_neopixel_switch_test
arduino-cli compile -b arduino:avr:nano .
arduino-cli upload -b arduino:avr:nano -p /dev/ttyUSB0 .
```

포트는 `arduino-cli board list` 로 확인. 실패 시 `arduino:avr:nano:cpu=atmega328old` 사용.

이전에 `dialout` 그룹·`arduino-cli` 설치가 안 되어 있으면 `../nano_neopixel_emotion_test/README.md` 참고.

## e-ink 와 동시에 쓰기 (Pi)

1. Arduino Nano를 Pi USB에 연결 (시리얼 포트 확인: `ttyACM0` 또는 `ttyUSB0`).
2. **같은 USB**로 시리얼을 읽으므로, `emotion_serial_eink.py` 실행 중에는 그 포트를 다른 프로그램이 열지 말 것.
3. Pi 터미널에서 (시스템 pip 가 막히면 venv 사용 — `rpi-eink-test/README.md` 참고):

```bash
export E_PAPER_ROOT="$HOME/e-Paper/RaspberryPi_JetsonNano/python"
source ~/Lingering-Lines/.venv/bin/activate   # 이미 만들어 둔 경우
pip install -r ~/Lingering-Lines/rpi-eink-test/requirements.txt
python3 ~/Lingering-Lines/rpi-eink-test/emotion_serial_eink.py --serial /dev/ttyUSB0
```

포트는 `ttyACM0` 일 수도 있고 `ttyUSB0` 일 수도 있음 — `ls /dev/ttyUSB* /dev/ttyACM*` 로 확인. 환경 변수 `ARDUINO_SERIAL` 로 기본 포트 지정 가능.
