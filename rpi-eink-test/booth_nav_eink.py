#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
부스 스토리 e-ink 네비게이션 (Arduino nano_booth_nav.ino 와 짝).

스위치 → 시리얼: BTN:BACK / BTN:OK / BTN:NEXT
Pi → Arduino: PLAY:<0-6> (Bring 페이지 5초 후 15초 네오; 난수는 Pi 에서 균등 선택)

실행:
  export E_PAPER_ROOT=\"$HOME/e-Paper/RaspberryPi_JetsonNano/python\"
  source ~/Lingering-Lines/.venv/bin/activate
  python3 ~/Lingering-Lines/rpi-eink-test/booth_nav_eink.py --serial /dev/ttyUSB0
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import sys
import time

os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

# 부스 본문: DejaVu 등 TTF 의 size 는 대략적인 픽셀 높이(표시에서 흔히 “pt”처럼 지정)
BOOTH_FONT_SIZE = 20
BOOTH_LINE_SPACING = 8

# "select로 말하기 준비" 페이지에서 OK 후 흰 화면 유지(초)
READY_WHITE_HOLD_S = 5.0

# e-ink: 전체 갱신은 (1) 최초 시작 시 한 번 (2) 마지막 페이지 10초 후 첫 페이지로 복귀할 때만.
# 그 외 페이지 이동은 display_Partial 만 사용(잔상은 phase 끝 전체 갱신으로 정리).

# 스토리 페이지 (한 줄 = 한 화면)
PAGES: list[str] = [
    "Spaces remember.",
    "People pass,\nbut something stays.",
    "Feelings settle quietly in the air.",
    "This place is filled with\nwhat came before you.",
    "Take a moment to listen.",
    "Something has been\nleft here before you.",
    "Would you like to follow the trace?",
    "Bring the receiver close.",
    "Now, it is your turn.",
    "Say what was never said.",
    'No one else will hear it.\nOnly the emotion will remain.',
    "Be honest with what you feel.",
    'When you are ready,\npress "select" and begin speaking.',
    'Press "select" to finish.',
    "Please place the receiver back.",
    "Only the feeling within\nyour message remains here.",
    "As it lingers in this space,\nothers who pass through will feel\nwhat you left behind.",
    "Emotions do not disappear.",
    "They move from\none person to another.",
    "Today, we are always connected.\nYet something feels distant.",
    "Our words travel fast, but\nour feelings do not always follow.",
    "This phone booth was once\nmeant for voices.\n\nFor words that needed\nsomewhere to go.",
    "But some things are never said.\n\nSo they stay.",
    "Here,\nconnection happens differently.",
    "Not through speed,\nbut through what lingers.",
    "You have followed\nsomeone else's trace.",
    "Now, you become a trace yourself.",
    "Thank you for being here.\n\nMay something of this\nstay with you.",
]

# 인덱스 상수 (위 배열과 동기화)
I_FOLLOW = 6
I_BRING = 7
I_NOW = 8
I_READY_SPEAK = 12
I_PRESS_FINISH = 13
I_PLACE = 14
I_THANKS = len(PAGES) - 1

BTN_BACK = re.compile(r"^BTN:BACK\s*$")
BTN_OK = re.compile(r"^BTN:OK\s*$")
BTN_NEXT = re.compile(r"^BTN:NEXT\s*$")


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


def _line_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> float:
    try:
        return float(draw.textlength(text, font=font))
    except AttributeError:
        if hasattr(font, "getlength"):
            return float(font.getlength(text))
        bbox = draw.textbbox((0, 0), text, font=font)
        return float(bbox[2] - bbox[0])


def _break_oversized_word(
    word: str, font: ImageFont.ImageFont, draw: ImageDraw.ImageDraw, max_w: float
) -> list[str]:
    """한 단어가 max_w 보다 길면 글자 단위로 잘라 여러 줄에 넣음."""
    out: list[str] = []
    chunk = ""
    for ch in word:
        trial = chunk + ch
        if _line_width(draw, trial, font) <= max_w:
            chunk = trial
        else:
            if chunk:
                out.append(chunk)
            chunk = ch
    if chunk:
        out.append(chunk)
    return out if out else [word[:1]]


def wrap_for_epd(text: str, width_px: int, height_px: int, margin: int) -> tuple[ImageFont.ImageFont, list[str]]:
    """고정 BOOTH_FONT_SIZE, 가로 픽셀 폭 기준으로 단어 줄바꿈."""
    font = load_font(BOOTH_FONT_SIZE)
    max_w = float(width_px - 2 * margin)
    draw = ImageDraw.Draw(Image.new("1", (1, 1)))
    lines: list[str] = []

    for raw_block in text.replace("\r\n", "\n").split("\n"):
        block = raw_block.strip()
        if not block:
            lines.append("")
            continue
        words = block.split()
        if not words:
            continue
        current = words[0]
        if _line_width(draw, current, font) > max_w:
            parts = _break_oversized_word(current, font, draw, max_w)
            lines.extend(parts[:-1])
            current = parts[-1]
        for w in words[1:]:
            trial = current + " " + w
            if _line_width(draw, trial, font) <= max_w:
                current = trial
            else:
                lines.append(current)
                if _line_width(draw, w, font) > max_w:
                    parts = _break_oversized_word(w, font, draw, max_w)
                    lines.extend(parts[:-1])
                    current = parts[-1]
                else:
                    current = w
        lines.append(current)

    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()

    if not lines:
        lines = [""]

    return font, lines


def render_screen(width: int, height: int, body: str) -> Image.Image:
    margin = 10
    font, lines = wrap_for_epd(body, width, height, margin)
    text = "\n".join(lines)
    img = Image.new("1", (width, height), 255)
    draw = ImageDraw.Draw(img)
    draw.multiline_text(
        (width // 2, height // 2),
        text,
        font=font,
        fill=0,
        anchor="mm",
        align="center",
        spacing=BOOTH_LINE_SPACING,
    )
    return img


class BoothState:
    __slots__ = (
        "page",
        "p7_t0",
        "p7_neo_sent",
        "p7_jump_scheduled",
        "thanks_until",
        "after_ready_white_until",
    )

    def __init__(self) -> None:
        self.page = 0
        self.p7_t0: float | None = None
        self.p7_neo_sent = False
        self.p7_jump_scheduled = False
        self.thanks_until: float | None = None
        self.after_ready_white_until: float | None = None

    def reset_loop(self) -> None:
        self.page = 0
        self.p7_t0 = None
        self.p7_neo_sent = False
        self.p7_jump_scheduled = False
        self.thanks_until = None
        self.after_ready_white_until = None


def show_partial(epd, buf) -> None:
    epd.display_Partial(buf)


def handle_back(st: BoothState) -> bool:
    if st.after_ready_white_until is not None:
        return False
    p = st.page
    if p == I_THANKS:
        return False
    if p <= I_FOLLOW:
        st.page = max(0, p - 1)
        return True
    if p == I_BRING:
        return False
    if p == I_NOW:
        return False
    if I_NOW < p <= I_READY_SPEAK:
        st.page = max(I_NOW, p - 1)
        return True
    if p == I_PRESS_FINISH:
        return False
    if p == I_PLACE:
        return False
    if I_PLACE < p < I_THANKS:
        st.page = max(I_PLACE, p - 1)
        return True
    return False


def handle_next(st: BoothState) -> bool:
    if st.after_ready_white_until is not None:
        return False
    p = st.page
    if p == I_THANKS:
        return False
    if p == I_FOLLOW:
        return False
    if p == I_BRING:
        return False
    if p == I_READY_SPEAK:
        return False
    if p == I_PRESS_FINISH:
        return False
    if p < I_THANKS:
        st.page = p + 1
        if st.page == I_THANKS:
            st.thanks_until = time.monotonic() + 10.0
        return True
    return False


def handle_ok(st: BoothState) -> bool:
    if st.after_ready_white_until is not None:
        return False
    p = st.page
    if p == I_THANKS:
        return False
    if p == I_FOLLOW:
        st.page = I_BRING
        st.p7_t0 = time.monotonic()
        st.p7_neo_sent = False
        st.p7_jump_scheduled = False
        return True
    if p == I_READY_SPEAK:
        st.after_ready_white_until = time.monotonic() + READY_WHITE_HOLD_S
        return True
    if p == I_PRESS_FINISH:
        st.page = I_PLACE
        return True
    return False


def tick_page7(st: BoothState, ser) -> bool:
    """Bring 페이지: 5초 후 PLAY:<0-6>(Pi secrets 균등), 이어서 Neo 15초 후 자동 I_NOW. 변경 시 True."""
    if st.page != I_BRING or st.p7_t0 is None:
        return False
    now = time.monotonic()
    dt = now - st.p7_t0
    changed = False
    _bring_delay_s = 5.0
    _neo_duration_s = 15.0
    if not st.p7_neo_sent and dt >= _bring_delay_s:
        emo_i = secrets.randbelow(7)
        ser.write(f"PLAY:{emo_i}\n".encode())
        ser.flush()
        st.p7_neo_sent = True
    if st.p7_neo_sent and not st.p7_jump_scheduled and dt >= _bring_delay_s + _neo_duration_s:
        st.page = I_NOW
        st.p7_jump_scheduled = True
        st.p7_t0 = None
        changed = True
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="부스 스토리 e-ink (nano_booth_nav)")
    parser.add_argument("--serial", "-p", default=os.environ.get("ARDUINO_SERIAL", "/dev/ttyACM0"))
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    try:
        import serial  # type: ignore[import-untyped]
    except ImportError:
        print("pyserial 이 필요합니다.", file=sys.stderr)
        return 1

    setup_waveshare_path()
    from waveshare_epd import epd4in2_V2  # pylint: disable=import-error

    try:
        ser = serial.Serial(
            args.serial,
            args.baud,
            timeout=0.08,
            rtscts=False,
            dsrdtr=False,
        )
    except OSError as exc:
        print(f"시리얼 열기 실패: {exc}", file=sys.stderr)
        return 1

    time.sleep(1.5)

    epd = epd4in2_V2.EPD()
    st = BoothState()

    print("e-ink 초기화…", flush=True)
    epd.init()
    epd.Clear()
    time.sleep(0.4)

    def draw() -> None:
        if (
            st.after_ready_white_until is not None
            and time.monotonic() < st.after_ready_white_until
        ):
            blank = Image.new("1", (epd.width, epd.height), 255)
            buf = epd.getbuffer(blank)
            show_partial(epd, buf)
            return
        buf = epd.getbuffer(render_screen(epd.width, epd.height, PAGES[st.page]))
        show_partial(epd, buf)

    buf_first = epd.getbuffer(render_screen(epd.width, epd.height, PAGES[st.page]))
    epd.display(buf_first)
    print(f"부스 UI 시작 ({args.serial}). Ctrl+C 종료", flush=True)

    try:
        while True:
            if st.page == I_THANKS and st.thanks_until is not None:
                if time.monotonic() >= st.thanks_until:
                    st.reset_loop()
                    epd.init()
                    epd.Clear()
                    time.sleep(0.3)
                    buf0 = epd.getbuffer(render_screen(epd.width, epd.height, PAGES[0]))
                    epd.display(buf0)
                    if args.debug:
                        print("[booth] 루프 초기화 → 페이지 0", flush=True)
                    continue

            if st.after_ready_white_until is not None and time.monotonic() >= st.after_ready_white_until:
                st.page = I_PRESS_FINISH
                st.after_ready_white_until = None
                draw()
                continue

            if tick_page7(st, ser):
                draw()
                continue

            if st.after_ready_white_until is not None:
                time.sleep(0.03)
                continue

            line = ser.readline()
            if not line:
                time.sleep(0.02)
                continue
            try:
                s = line.decode("utf-8", errors="replace").strip()
            except Exception:
                continue
            if not s:
                continue
            if args.debug:
                print(f"[serial] {s!r}", file=sys.stderr, flush=True)

            acted = False
            if BTN_BACK.match(s):
                acted = handle_back(st)
            elif BTN_OK.match(s):
                acted = handle_ok(st)
            elif BTN_NEXT.match(s):
                acted = handle_next(st)

            if acted:
                draw()
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
