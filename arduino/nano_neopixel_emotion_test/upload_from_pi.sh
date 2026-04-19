#!/usr/bin/env bash
# 라즈베리파이에서 Nano에 NeoPixel 테스트 스케치 업로드
# 사용법:
#   chmod +x upload_from_pi.sh
#   ./upload_from_pi.sh /dev/ttyACM0
#   ./upload_from_pi.sh          # 첫 번째 ACM/USB 자동 시도

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${1:-}"

if ! command -v arduino-cli >/dev/null 2>&1; then
  echo "arduino-cli 가 없습니다. README.md 의 설치 단계를 먼저 실행하세요."
  exit 1
fi

arduino-cli core update-index >/dev/null 2>&1 || true
arduino-cli core install arduino:avr 2>/dev/null || true
arduino-cli lib install "Adafruit NeoPixel" 2>/dev/null || true

if [[ -z "$PORT" ]]; then
  PORT="$(arduino-cli board list | awk '/arduino:avr:nano|ttyACM|ttyUSB/ {print $1; exit}')"
fi
if [[ -z "$PORT" || ! -e "$PORT" ]]; then
  echo "시리얼 포트를 찾지 못했습니다. 수동 지정: $0 /dev/ttyACM0"
  arduino-cli board list
  exit 1
fi

echo "Using port: $PORT"
FQBN_OLD="arduino:avr:nano:cpu=atmega328old"
FQBN_NEW="arduino:avr:nano"

arduino-cli compile -b "$FQBN_OLD" "$DIR" || {
  echo "Retry compile with $FQBN_NEW ..."
  arduino-cli compile -b "$FQBN_NEW" "$DIR"
  arduino-cli upload -b "$FQBN_NEW" -p "$PORT" "$DIR"
  exit 0
}
arduino-cli upload -b "$FQBN_OLD" -p "$PORT" "$DIR"
echo "Upload OK."
