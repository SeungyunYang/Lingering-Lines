# NeoPixel 감정 오로라 테스트 (Arduino Nano)

## 목적

전체 인터랙션 전에 **NeoPixel만** 연결해 두고, **6개 픽셀마다 한 그룹**으로 나눠 그룹마다 (시작색→끝색) 그라데이션을 넣습니다. **숨쉬기**는 `millis()`로 그룹 **내부** 보간만 살짝 움직이며, 불이 스트립 전체 길이를 따라 흘러가지는 않습니다.

## 하드웨어 (요약)

- NeoPixel **DIN → D7** (330Ω 직렬)
- 스트립 **전원은 외부 5V**, Arduino 5V와 **+끼리 연결하지 않음**
- **GND 공통**: Arduino GND, 외부 PSU GND, NeoPixel GND

## 코드에서 바꿀 것

`nano_neopixel_emotion_test.ino` 상단:

```cpp
#define ACTIVE_EMOTION 0
```

| 값 | 감정     | 느낌 (팔레트)   |
|----|----------|-----------------|
| 0  | JOY      | 6구간 노랑·주황·연두빛 조합 (코드 `JOY_SEGS` 참고) |
| 1  | SADNESS  | 파랑 계열      |
| 2  | ANGER    | 빨강 계열      |
| 3  | FEAR     | 보라/짙은 계열 |
| 4  | LOVE     | 핑크·코랄·따뜻한 레드 (`LOVE_SEGS`) |
| 5  | DISGUST  | 올리브·역녹 (채도 있음, 푸른빛 없음) |
| 6  | NEUTRAL  | 웜그레이·실버 (저채도 중립) |

숫자만 바꿔서 업로드할 때마다 한 가지 감정만 테스트합니다.

- `NUM_PIXELS`는 **`GROUP_SIZE`(6)의 배수**여야 합니다 (예: 36).
- 그룹별 시작/끝 RGB는 감정마다 `*_SEGS` 배열에서 수정합니다.
- 숨쉬기: `BREATH_SPEED`(속도), `BREATH_AMP`(큰 물결), `BREATH_SHIMMER_AMP` / `BREATH_SHIMMER_MULT`(그룹 안 빠른 잔물결).

## 라이브러리

- [Adafruit NeoPixel](https://github.com/adafruit/Adafruit_NeoPixel)

## 라즈베리파이 5에서 USB로 업로드 (arduino-cli)

Pi에 SSH 접속한 뒤:

### 1) arduino-cli 설치 (한 번)

**현재 디렉터리**에서 `install.sh`를 실행하면 바이너리가 `./bin`(예: `~/Lingering-Lines/bin`)에 들어갑니다. `PATH`에 그 경로를 넣거나, 아래처럼 **설치 위치를 고정**하세요.

```bash
mkdir -p "$HOME/bin"
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR="$HOME/bin" sh
export PATH="$PATH:$HOME/bin"
arduino-cli version
```

이미 repo 루트 등에 설치-only 된 경우:

```bash
export PATH="$PATH:$HOME/Lingering-Lines/bin"   # 경로는 설치 로그의 "installed successfully in ..." 와 동일하게
arduino-cli version
```

### 2) 코어 + 라이브러리

```bash
arduino-cli core update-index
arduino-cli core install arduino:avr
arduino-cli lib install "Adafruit NeoPixel"
```

### 3) 보드·포트 확인

Nano를 USB로 Pi에 연결:

```bash
arduino-cli board list
```

보통 `Serial Port`가 `/dev/ttyUSB0` 또는 `/dev/ttyACM0` 입니다.

### 4) 컴파일 & 업로드

프로젝트 경로(예: `~/Lingering-Lines`)에 스케치가 있을 때:

```bash
cd ~/Lingering-Lines/arduino/nano_neopixel_emotion_test
arduino-cli compile -b arduino:avr:nano:cpu=atmega328old .
arduino-cli upload -b arduino:avr:nano:cpu=atmega328old -p /dev/ttyACM0 .
```

- 업로드 실패 시 부트로더에 따라 `cpu=atmega328` 로 바꿔 보세요:

```bash
arduino-cli compile -b arduino:avr:nano .
arduino-cli upload -b arduino:avr:nano -p /dev/ttyACM0 .
```

### 5) 권한 (필요 시)

```bash
sudo usermod -aG dialout $USER
```

로그아웃 후 다시 로그인하거나 새 SSH 세션에서 진행합니다.

## 참고

- `NUM_PIXELS`, `BRIGHTNESS_MAX`는 스트립 길이/밝기에 맞게 조정하세요.
- 이 스케치는 **버튼·DRV2605·시리얼** 없이 NeoPixel만 사용합니다.
