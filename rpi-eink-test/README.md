# Raspberry Pi + Waveshare 4.2" e-Paper (V2) 테스트

## 질문에 대한 답

1. **이미지 파일 없이 코드에 넣은 텍스트만 띄울 수 있나?**  
   **가능합니다.** 내부적으로는 PIL이 글자를 **비트맵(픽셀)**으로 그린 뒤, 그 결과를 `epd.getbuffer()`로 패널에 보냅니다. 별도 `.bmp` 파일이 필요 없습니다.

2. **가로·세로 중앙 정렬?**  
   **가능합니다.** `typewriter_demo.py`의 `render_centered()`가 `multiline_text(..., anchor="mm", align="center")`로 블록 중심을 화면 중앙에 둡니다.

3. **타자기처럼 빠르게 탁탁?**  
   **물리적으로 한계가 있습니다.**  
   - 전체 갱신(`display`)은 대략 **수 초** 단위.  
   - V2 **Fast**(`display_Fast`)도 **글자마다** 호출하면 체감상 빠른 LCD/모니터의 타자기와는 다릅니다.  
   - **부분 갱신**(`display_Partial`)이 상대적으로 덜 느리게 느껴질 수 있지만, 여러 번 반복하면 **잔상**이 생기므로 주기적으로 **전체 갱신**이 필요합니다.  
   → [Waveshare 4.2" 매뉴얼](https://www.waveshare.com/wiki/4.2inch_e-Paper_Module_Manual#Working_With_Raspberry_Pi)의 주의사항을 참고하세요.

## 실행 방법 (라즈베리파이에서)

1. SPI 켜기, 배선은 [Waveshare Wiki](https://www.waveshare.com/wiki/4.2inch_e-Paper_Module_Manual#Working_With_Raspberry_Pi) 참고.

2. 공식 예제 받기:
   ```bash
   git clone https://github.com/waveshare/e-Paper.git
   ```

3. 환경 변수로 `lib` 위치 지정 후 실행:
   ```bash
   export E_PAPER_ROOT="$HOME/e-Paper/RaspberryPi_JetsonNano/python"
   cd /path/to/Lingering-Lines/rpi-eink-test
   chmod +x typewriter_demo.py
   python3 typewriter_demo.py
   ```

4. 옵션 예:
   ```bash
   # 최종 문장만 한 번 (타자기 없음)
   python3 typewriter_demo.py --static-only -m "Hello, e-Paper."

   # Fast 모드 타자기 (기본)
   python3 typewriter_demo.py --mode fast --char-step 1 --delay 0

   # 부분 갱신 (8글자마다 전체 갱신으로 잔상 완화)
   python3 typewriter_demo.py --mode partial --partial-full-every 8
   ```

5. **Pi 5**: Waveshare 저장소의 `epdconfig`가 Pi 5 / 새 커널에서 동작하는지 확인하세요. 문제가 있으면 Waveshare GitHub 이슈·위키를 참고합니다.

## Arduino 스위치 → e-ink 감정 표시

`nano_neopixel_switch_test.ino` 를 Nano에 올린 뒤, USB로 Pi와 연결하면 시리얼로 `EMO:` / `LED:` 줄이 나옵니다. 이를 받아 화면에 `JOY`, `SADNESS` … 를 띄우려면:

**의존성 (택 1)**

- **가상환경 (PEP 668 회피 — 권장):**
  ```bash
  cd ~/Lingering-Lines
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r rpi-eink-test/requirements.txt
  ```
- **또는 apt:** `sudo apt install python3-serial python3-pil` (시스템 `python3`로 실행)

**실행** (시리얼 포트는 보드마다 다름 — 아래 참고):

```bash
export E_PAPER_ROOT="$HOME/e-Paper/RaspberryPi_JetsonNano/python"
# venv 썼으면: source ~/Lingering-Lines/.venv/bin/activate
python3 rpi-eink-test/emotion_serial_eink.py --serial /dev/ttyUSB0
```

**시리얼 포트:** `ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null` 또는 `arduino-cli board list` 로 확인. CH340 Nano는 보통 **`/dev/ttyUSB0`**, 다른 보드는 **`/dev/ttyACM0`** 인 경우가 많습니다. 없으면 USB 재연결·케이블·`dialout` 그룹을 확인하세요.

## 부스 스토리 e-ink (`nano_booth_nav.ino`)

스위치만으로 페이지를 넘기는 **별도** 펌웨어·스크립트입니다. `nano_neopixel_switch_test` 대신 `arduino/nano_booth_nav/` 를 업로드한 뒤:

```bash
export E_PAPER_ROOT="$HOME/e-Paper/RaspberryPi_JetsonNano/python"
source ~/Lingering-Lines/.venv/bin/activate   # 선택
python3 ~/Lingering-Lines/rpi-eink-test/booth_nav_eink.py --serial /dev/ttyUSB0
```

상세 업로드: `arduino/nano_booth_nav/README.md` 참고.

## 코드에서 바꿀 곳

`typewriter_demo.py` 상단의 **`DEFAULT_MESSAGE`** 문자열을 수정하면 기본 표시 문구가 바뀝니다.
