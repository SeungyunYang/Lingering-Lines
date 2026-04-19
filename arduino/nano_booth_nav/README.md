# 부스 e-ink 네비게이션용 Arduino (nano_booth_nav)

## 역할

- **D2 Back / D3 OK(Select) / D5 Next** 스위치를 읽어 USB 시리얼로 `BTN:BACK`, `BTN:OK`, `BTN:NEXT` 한 줄씩 전송 (눌림 에지, 115200).
- **NeoPixel(D7)** 은 라즈베리파이가 보내는 명령으로만 점등:
  - `PLAY:RANDOM` — 7감정 중 하나를 15초간 재생 후 소등
  - `PLAY:<0-6>` — 해당 감정 15초 재생 후 소등
- **DRV2605L** (I²C `0x5A`): NeoPixel 재생과 같은 동안 ROM 웨이폼 **88번**을 반복(한 번 끝나면 다시 `go()`). Neo가 꺼지면 `stop()`.

### 배선 (Arduino Nano)

| DRV2605L 보드 | Nano |
|---------------|------|
| VIN / VCC | 5V 또는 3.3V (보드 허용 범위) |
| GND | GND |
| SDA | **A4** |
| SCL | **A5** |
| 모터 | 보드의 OUT+/OUT− (코인 햅틱 데이터시트대로) |

- 라이브러리: **Adafruit DRV2605** (`arduino-cli lib install "Adafruit DRV2605 Library"` — BusIO 의존성 자동).
- 스케치는 **ERM** 모드(`useERM()`). 코인 모터가 LRA 계열이면 `nano_booth_nav.ino` 의 `setup()` 에서 `useLRA()` 로 바꿔 볼 것.
- I²C 실패 시(`begin()` false) NeoPixel·버튼만 동작하고 햅틱은 건너뜀.

감정 팔레트는 `nano_neopixel_switch_test.ino` 와 동일한 7종.

## Pi에서 업로드

```bash
cd ~/Lingering-Lines/arduino/nano_booth_nav
arduino-cli board list
arduino-cli compile -b arduino:avr:nano .
arduino-cli upload -b arduino:avr:nano -p /dev/ttyUSB0 .
```

실패 시:

```bash
arduino-cli compile -b arduino:avr:nano:cpu=atmega328old .
arduino-cli upload -b arduino:avr:nano:cpu=atmega328old -p /dev/ttyUSB0 .
```

업로드 전에 `emotion_serial_eink.py` / `booth_nav_eink.py` 등 **같은 시리얼 포트를 쓰는 프로그램은 종료**하세요.

## 라이브러리

- [Adafruit NeoPixel](https://github.com/adafruit/Adafruit_NeoPixel) (`arduino-cli lib install "Adafruit NeoPixel"`)
- [Adafruit DRV2605](https://github.com/adafruit/Adafruit_DRV2605_Library) (`arduino-cli lib install "Adafruit DRV2605 Library"`)
