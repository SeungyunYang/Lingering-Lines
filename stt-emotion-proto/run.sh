#!/bin/bash
# 시스템 Python 대신 Homebrew Python으로 실행 (macOS tkinter 오류 방지)
cd "$(dirname "$0")"

if [ -x /opt/homebrew/bin/python3 ]; then
  exec /opt/homebrew/bin/python3 app.py
elif [ -x /usr/local/bin/python3 ]; then
  exec /usr/local/bin/python3 app.py
else
  echo "Homebrew Python이 없습니다. 다음으로 설치 후 다시 실행하세요:"
  echo "  brew install python-tk"
  exit 1
fi
