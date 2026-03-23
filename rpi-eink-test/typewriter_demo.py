#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Waveshare 4.2" e-Paper V2 (400x300) + Raspberry Pi 테스트용 스크립트.

- 코드에 넣은 문자열을 화면 가로·세로 중앙에 표시 (PIL로 그린 뒤 e-ink로 전송)
- 타자기 효과: 글자를 하나씩(또는 한 덩어리씩) 늘려가며 갱신

주의 (e-ink 특성):
  - 전체 갱신은 수 초 단위로 느림. V2의 Fast 모드도 글자마다 호출하면 체감상 "탁탁"보다는 느린 편.
  - 부분 갱신(display_Partial)은 더 빠르게 보일 수 있으나, 여러 번 반복 후에는
    잔상이 쌓이므로 주기적으로 전체 갱신이 필요함 (Waveshare 매뉴얼 권장).

사전 준비:
  1) SPI 활성화, 핀 연결은 Waveshare 매뉴얼 참고
     https://www.waveshare.com/wiki/4.2inch_e-Paper_Module_Manual#Working_With_Raspberry_Pi
  2) 공식 저장소 클론 후 이 스크립트를 examples 옆에 두거나 PYTHONPATH 설정:

     git clone https://github.com/waveshare/e-Paper.git
     export E_PAPER_ROOT="$HOME/e-Paper/RaspberryPi_JetsonNano/python"
     python3 typewriter_demo.py

  또는 이 파일을 e-Paper/RaspberryPi_JetsonNano/python/examples/ 에 복사한 뒤
  상위의 lib 가 import 되도록 실행.

Raspberry Pi 5: Waveshare 최신 e-Paper 코드의 epdconfig가 Pi 5를 지원하는지 확인하세요.
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
import time

# --- Waveshare lib 경로 ---
def _setup_waveshare_path() -> str | None:
    env = os.environ.get("E_PAPER_ROOT")
    if env and os.path.isdir(os.path.join(env, "lib")):
        sys.path.insert(0, os.path.join(env, "lib"))
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "lib"),
        os.path.join(here, "..", "e-Paper", "RaspberryPi_JetsonNano", "python", "lib"),
        os.path.join(os.path.expanduser("~"), "e-Paper", "RaspberryPi_JetsonNano", "python", "lib"),
    ]
    for lib in candidates:
        lib = os.path.normpath(lib)
        if os.path.isdir(lib):
            sys.path.insert(0, lib)
            return os.path.dirname(lib)
    return None


EPAPER_BASE = _setup_waveshare_path()
if EPAPER_BASE is None:
    print(
        "waveshare_epd 를 찾을 수 없습니다.\n"
        "  export E_PAPER_ROOT=/path/to/e-Paper/RaspberryPi_JetsonNano/python\n"
        "또는 위 경로에 lib/waveshare_epd 가 있도록 클론하세요.",
        file=sys.stderr,
    )
    sys.exit(1)

from waveshare_epd import epd4in2_V2  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

# 화면에 쓸 문장 (여기만 바꿔서 테스트)
DEFAULT_MESSAGE = (
    "Hello from Lingering Lines.\n"
    "This is centered text on 4.2 inch e-Paper.\n"
    "Typewriter effect below…"
)

# 폰트 후보 (라즈베리파이 / Debian 계열)
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    # Waveshare 예제 번들 (E_PAPER_ROOT/pic/Font.ttc)
    pic = os.path.join(EPAPER_BASE or "", "pic", "Font.ttc")
    if os.path.isfile(pic):
        return ImageFont.truetype(pic, size)
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    if not text.strip():
        return 0, 0
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def wrap_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        wrapped = textwrap.wrap(
            paragraph,
            width=999,
            break_long_words=True,
            break_on_hyphens=False,
        )
        current: list[str] = []
        for word in paragraph.split():
            trial = (" ".join(current + [word])) if current else word
            w, _ = text_size(draw, trial, font)
            if w <= max_width or not current:
                current.append(word)
            else:
                lines.append(" ".join(current))
                current = [word]
        if current:
            lines.append(" ".join(current))
    return "\n".join(lines)


def render_centered(
    width: int,
    height: int,
    text: str,
    font: ImageFont.ImageFont,
    margin: int = 12,
) -> Image.Image:
    """흰 배경에 검은 글자, 가로·세로 중앙 정렬."""
    img = Image.new("1", (width, height), 255)
    draw = ImageDraw.Draw(img)
    max_w = width - 2 * margin
    wrapped = wrap_to_width(draw, text, font, max_w)
    # multiline_text + anchor="mm" : 블록 중심을 (cx, cy)에
    cx, cy = width // 2, height // 2
    draw.multiline_text(
        (cx, cy),
        wrapped,
        font=font,
        fill=0,
        anchor="mm",
        align="center",
        spacing=6,
    )
    return img


def run_typewriter(
    epd: epd4in2_V2.EPD,
    full_message: str,
    *,
    mode: str,
    char_step: int,
    delay_sec: float,
    font_size: int,
    partial_every_full: int,
) -> None:
    """
    mode:
      fast  — init_fast + display_Fast (V2 빠른 갱신, 그래도 글자당 수백 ms~1초대)
      full  — init + display (가장 느리지만 깨끗)
      partial — display_Partial (잔상 주의; N회마다 full로 정리)
    """
    font = load_font(font_size)
    w, h = epd.width, epd.height

    if mode == "full":
        epd.init()
        epd.Clear()
    elif mode == "partial":
        # 부분 갱신 전에 한 번 전체 초기화하는 편이 안정적 (Waveshare 예제와 동일 계열)
        epd.init()
        epd.Clear()
        epd.init_fast(epd.Seconds_1S)
    else:
        epd.init_fast(epd.Seconds_1S)

    partial_count = 0
    n = len(full_message)
    end = 0  # 0이면 빈 화면 한 프레임(건너뛰려면 아래 range 시작을 1로)
    while True:
        chunk = full_message[:end]
        img = render_centered(w, h, chunk, font)
        buf = epd.getbuffer(img)

        if mode == "full":
            epd.display(buf)
        elif mode == "fast":
            epd.display_Fast(buf)
        else:
            epd.display_Partial(buf)
            partial_count += 1
            if partial_count >= partial_every_full:
                epd.init()
                epd.display(buf)
                partial_count = 0
                epd.init_fast(epd.Seconds_1S)

        if delay_sec > 0:
            time.sleep(delay_sec)

        if end >= n:
            break
        end = min(end + char_step, n)

    cleanup_epd(epd)


def cleanup_epd(epd: epd4in2_V2.EPD) -> None:
    try:
        epd.init()
        epd.Clear()
        epd.sleep()
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="4.2\" e-Paper centered text + typewriter demo")
    parser.add_argument("--message", "-m", default=DEFAULT_MESSAGE, help="표시할 텍스트 (\\n 허용)")
    parser.add_argument(
        "--mode",
        choices=("fast", "full", "partial"),
        default="fast",
        help="갱신 방식: fast(권장 테스트), full(느림), partial(빠르지만 잔상)",
    )
    parser.add_argument("--char-step", type=int, default=1, help="한 번에 추가할 글자 수")
    parser.add_argument("--delay", type=float, default=0.05, help="각 스텝 사이 대기(초). e-ink가 느리면 0 권장")
    parser.add_argument("--font-size", type=int, default=22)
    parser.add_argument(
        "--partial-full-every",
        type=int,
        default=8,
        help="partial 모드에서 N스텝마다 전체 갱신으로 잔상 완화",
    )
    parser.add_argument("--static-only", action="store_true", help="타자기 없이 최종 문장만 한 번 표시")
    args = parser.parse_args()

    epd = epd4in2_V2.EPD()
    font = load_font(args.font_size)
    w, h = epd.width, epd.height

    if args.static_only:
        epd.init()
        epd.Clear()
        img = render_centered(w, h, args.message, font)
        epd.display(epd.getbuffer(img))
        time.sleep(2)
        cleanup_epd(epd)
        return

    run_typewriter(
        epd,
        args.message,
        mode=args.mode,
        char_step=max(1, args.char_step),
        delay_sec=max(0.0, args.delay),
        font_size=args.font_size,
        partial_every_full=max(1, args.partial_full_every),
    )


if __name__ == "__main__":
    main()
