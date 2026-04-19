#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Waveshare 4.2" e-Paper (V2, 400x300) 연결 확인용 스크립트.

표시 순서:
1) White clear
2) 체크 패턴/테두리/십자선
3) 중앙 텍스트 "E-INK OK"

실행:
  export E_PAPER_ROOT="$HOME/e-Paper/RaspberryPi_JetsonNano/python"
  python3 rpi-eink-test/test_eink_connection.py
"""

from __future__ import annotations

import os
import sys
import time

from PIL import Image, ImageDraw, ImageFont


def setup_waveshare_path() -> None:
    env_root = os.environ.get("E_PAPER_ROOT", "").strip()
    candidates = []
    if env_root:
        candidates.append(os.path.join(env_root, "lib"))
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.extend(
        [
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
        "waveshare_epd 라이브러리를 찾을 수 없습니다. "
        "E_PAPER_ROOT를 설정하거나 waveshare/e-Paper 저장소를 ~/e-Paper로 클론하세요."
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


def centered_text_image(width: int, height: int, text: str) -> Image.Image:
    img = Image.new("1", (width, height), 255)
    draw = ImageDraw.Draw(img)
    font = load_font(42)
    draw.multiline_text(
        (width // 2, height // 2),
        text,
        font=font,
        fill=0,
        anchor="mm",
        align="center",
        spacing=8,
    )
    return img


def pattern_image(width: int, height: int) -> Image.Image:
    img = Image.new("1", (width, height), 255)
    draw = ImageDraw.Draw(img)

    # 바깥 테두리 + 중앙 십자선
    draw.rectangle((0, 0, width - 1, height - 1), outline=0, width=2)
    draw.line((width // 2, 0, width // 2, height - 1), fill=0, width=1)
    draw.line((0, height // 2, width - 1, height // 2), fill=0, width=1)

    # 좌상단 체크 패턴
    block = 10
    for y in range(20, min(140, height), block):
        for x in range(20, min(220, width), block):
            if ((x // block) + (y // block)) % 2 == 0:
                draw.rectangle((x, y, x + block - 1, y + block - 1), fill=0)

    # 우하단 텍스트
    font = load_font(20)
    draw.text((width - 185, height - 35), "Pattern Check", font=font, fill=0)
    return img


def main() -> int:
    try:
        setup_waveshare_path()
        from waveshare_epd import epd4in2_V2  # pylint: disable=import-error

        epd = epd4in2_V2.EPD()
        print("[1/3] init + clear")
        epd.init()
        epd.Clear()
        time.sleep(1.0)

        print("[2/3] draw pattern")
        img_pat = pattern_image(epd.width, epd.height)
        epd.display(epd.getbuffer(img_pat))
        time.sleep(2.0)

        print("[3/3] draw centered text")
        img_ok = centered_text_image(epd.width, epd.height, "E-INK OK")
        epd.display(epd.getbuffer(img_ok))

        print("완료: 화면에 'E-INK OK'가 보이면 연결 정상입니다.")
        return 0
    except Exception as exc:
        print("실패:", exc)
        print("점검:")
        print("  - SPI enable 여부 (raspi-config)")
        print("  - 배선 (VCC/GND/DIN/CLK/CS/DC/RST/BUSY)")
        print("  - E_PAPER_ROOT 경로")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
