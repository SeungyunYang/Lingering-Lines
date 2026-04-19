#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arduino (nano_neopixel_switch_test.ino) USB 시리얼 → 감정 이름을 4.2\" e-ink 에 표시.

아두이노가 보내는 줄:
  EMO:<0-6>
  LED:<0|1>   (0 = NeoPixel 전체 끔, 1 = 켬)

실행 (Pi에서, Arduino USB 연결 후):
  export E_PAPER_ROOT=\"$HOME/e-Paper/RaspberryPi_JetsonNano/python\"
  pip install pyserial   # 필요 시
  python3 rpi-eink-test/emotion_serial_eink.py --serial /dev/ttyACM0

수신이 전혀 없을 때(--debug 도 조용함): 충전 전용 USB 케이블·다른 tty·펌웨어 미업로드 가능성.
  e-ink 스크립트를 끄고 `python3 rpi-eink-test/serial_listen.py -p /dev/ttyUSB0` 로 원시 바이트 확인.
  Arduino 에서 nano_neopixel_switch_test.ino 의 SERIAL_LINK_TEST 를 1로 업로드하면 주기적으로 LINK:줄이 옴.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time

# Pi 5 + gpiozero 백엔드 (epdconfig import 전에 설정)
os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")

from PIL import Image, ImageDraw, ImageFont  # noqa: E402


def setup_waveshare_path() -> None:
    env_root = os.environ.get("E_PAPER_ROOT", "").strip()
    candidates: list[str] = []
    if env_root:
        candidates.append(os.path.join(env_root, "lib"))
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.extend(
        [
            os.path.join(here, "lib"),
            os.path.join(here, "..", "e-Paper", "RaspberryPi_JetsonNano", "python", "lib"),
            os.path.join(os.path.expanduser("~"), "e-Paper", "RaspberryPi_JetsonNano", "python", "lib"),
        ]
    )
    for libdir in candidates:
        libdir = os.path.normpath(libdir)
        if os.path.isdir(libdir):
            sys.path.insert(0, libdir)
            return
    raise RuntimeError(
        "waveshare_epd 를 찾을 수 없습니다. export E_PAPER_ROOT=.../RaspberryPi_JetsonNano/python"
    )


EMOTION_LABELS = ("JOY", "SADNESS", "ANGER", "FEAR", "LOVE", "DISGUST", "NEUTRAL")

# 부분 갱신 횟수 후 전체 갱신 1회(잔상 제거). 시작 시 첫 display는 전체이므로 이후부터 카운트.
PARTIALS_BEFORE_FULL = 12

EMO_RE = re.compile(r"^EMO:([0-6])\s*$")
LED_RE = re.compile(r"^LED:([01])\s*$")


def load_font(size: int) -> ImageFont.ImageFont:
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for p in paths:
        if os.path.isfile(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def render_screen(width: int, height: int, emotion_i: int, lights_on: bool) -> Image.Image:
    name = EMOTION_LABELS[emotion_i]
    text = name if lights_on else f"{name}\n(NeoPixel OFF)"
    font_size = 46 if "\n" not in text else 38

    img = Image.new("1", (width, height), 255)
    draw = ImageDraw.Draw(img)
    font = load_font(font_size)
    draw.multiline_text(
        (width // 2, height // 2),
        text,
        font=font,
        fill=0,
        anchor="mm",
        align="center",
        spacing=14,
    )
    return img


def main() -> int:
    parser = argparse.ArgumentParser(description="Arduino 시리얼 → e-ink 감정 표시")
    parser.add_argument(
        "--serial",
        "-p",
        default=os.environ.get("ARDUINO_SERIAL", "/dev/ttyACM0"),
        help="Arduino USB 시리얼 (기본 /dev/ttyACM0, CH340이면 ttyUSB0)",
    )
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument(
        "--debug",
        action="store_true",
        help="시리얼로 받은 줄(매칭 실패 포함)을 stderr에 출력",
    )
    args = parser.parse_args()

    try:
        import serial  # type: ignore[import-untyped]
    except ImportError:
        print("pyserial 이 필요합니다: pip install pyserial", file=sys.stderr)
        return 1

    setup_waveshare_path()
    from waveshare_epd import epd4in2_V2  # pylint: disable=import-error

    try:
        # dsrdtr/rtscts: 일부 보드는 포트 열 때 DTR/RTS로 리셋·흐름 제어가 걸려 수신이 꼬일 수 있음
        ser = serial.Serial(
            args.serial,
            args.baud,
            timeout=0.2,
            rtscts=False,
            dsrdtr=False,
        )
    except OSError as exc:
        print(f"시리얼 열기 실패 ({args.serial}): {exc}", file=sys.stderr)
        return 1

    # 포트 오픈 시 Arduino가 리셋되면 setup()의 emitSerialState()가 잠시 뒤 옴. reset_input_buffer()로 지우면
    # 부팅 직후 한 줄도 안 보이는 것처럼 됨.
    time.sleep(1.5)

    epd = epd4in2_V2.EPD()
    emotion_i = 0
    lights_on = True

    print("e-ink 초기화 중…", flush=True)
    epd.init()
    epd.Clear()
    time.sleep(0.5)

    img0 = render_screen(epd.width, epd.height, emotion_i, lights_on)
    epd.display(epd.getbuffer(img0))
    partial_since_full = 0
    print(f"시리얼 대기 중 ({args.serial}). 스위치로 감정/LED 변경… Ctrl+C 종료", flush=True)

    try:
        while True:
            line = ser.readline()
            if not line:
                continue
            try:
                s = line.decode("utf-8", errors="replace").strip()
            except Exception:
                continue
            if not s:
                continue
            if args.debug:
                print(f"[serial] {s!r}", file=sys.stderr, flush=True)

            m = EMO_RE.match(s)
            if m:
                emotion_i = int(m.group(1))
                print(f"  EMO -> {EMOTION_LABELS[emotion_i]}", flush=True)
            else:
                m = LED_RE.match(s)
                if m:
                    lights_on = m.group(1) == "1"
                    print(f"  LED -> {'ON' if lights_on else 'OFF'}", flush=True)
                else:
                    continue

            buf = epd.getbuffer(render_screen(epd.width, epd.height, emotion_i, lights_on))
            if partial_since_full >= PARTIALS_BEFORE_FULL:
                epd.init()
                epd.display(buf)
                partial_since_full = 0
                if args.debug:
                    print(
                        f"  [e-ink] 전체 갱신 (잔상 제거, 부분 {PARTIALS_BEFORE_FULL}회 후)",
                        file=sys.stderr,
                        flush=True,
                    )
            else:
                epd.display_Partial(buf)
                partial_since_full += 1
    except KeyboardInterrupt:
        print("\n종료", flush=True)
    finally:
        ser.close()
        try:
            epd.sleep()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
