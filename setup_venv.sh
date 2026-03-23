#!/bin/bash
# macOS tkinter 오류 방지: Homebrew Python으로 .venv 재생성
set -e
cd "$(dirname "$0")"

PYTHON=""
if [ -x /opt/homebrew/bin/python3 ]; then
  PYTHON=/opt/homebrew/bin/python3
elif [ -x /usr/local/bin/python3 ]; then
  PYTHON=/usr/local/bin/python3
fi

if [ -z "$PYTHON" ]; then
  echo "Homebrew Python이 없습니다. 먼저 설치하세요:"
  echo "  brew install python-tk"
  exit 1
fi

echo "사용할 Python: $PYTHON"
$PYTHON --version

echo ""
echo "기존 .venv 제거 후 새로 만듭니다..."
rm -rf .venv
$PYTHON -m venv .venv

echo "가상환경 활성화 후 패키지 설치..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r stt-emotion-proto/requirements.txt

echo ""
echo "완료. Cursor에서 다음을 하세요:"
echo "  1. Cmd+Shift+P → 'Python: Select Interpreter'"
echo "  2. 목록에서 '.venv (Python ...)' 선택"
echo "  3. app.py 열고 재생 버튼으로 실행"
