#!/usr/bin/env python3
"""e-ink 없이 USB 시리얼만 덤프 (Arduino 수신 확인용).

  python3 rpi-eink-test/serial_listen.py -p /dev/ttyUSB0

emotion_serial_eink.py 를 끈 뒤 실행하세요. 같은 포트는 한 번에 한 프로세스만 열 수 있습니다.
"""
from __future__ import annotations

import argparse
import sys
import time

try:
    import serial  # type: ignore[import-untyped]
except ImportError:
    print("pyserial 필요: pip install pyserial", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    p = argparse.ArgumentParser(description="시리얼 원시 덤프 (디버그)")
    p.add_argument("-p", "--port", default="/dev/ttyUSB0")
    p.add_argument("-b", "--baud", type=int, default=115200)
    args = p.parse_args()

    ser = serial.Serial(
        args.port,
        args.baud,
        timeout=0.25,
        rtscts=False,
        dsrdtr=False,
    )
    print(f"열림 {args.port} @ {args.baud}. 수신 대기… Ctrl+C 종료", flush=True)
    time.sleep(1.5)

    try:
        while True:
            n = ser.in_waiting
            chunk = ser.read(4096 if n == 0 else n)
            if chunk:
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
            else:
                time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n종료", flush=True)
    finally:
        ser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
