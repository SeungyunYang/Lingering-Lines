#!/usr/bin/env bash
# backup_lingering_lines.sh 로 만든 .tar.gz 를 풀어 프로젝트 트리를 되돌립니다.
#
# 사용법:
#   ./scripts/restore_lingering_lines.sh ~/backups/lingering-lines/snapshot-XXX/Lingering-Lines-XXX.tar.gz
#   ./scripts/restore_lingering_lines.sh /path/to/archive.tar.gz /path/to/parent   # parent 아래에 Lingering-Lines 폴더 생성
#
# 주의: 대상에 같은 이름 폴더가 있으면 덮어쓰기 전에 백업하세요.
#
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "사용법: $0 <백업.tar.gz> [풀 상위 디렉터리 (기본: 홈의 Lingering-Lines 부모)]" >&2
  exit 1
fi

ARCHIVE="$(realpath "$1")"
if [[ ! -f "$ARCHIVE" ]]; then
  echo "파일 없음: $ARCHIVE" >&2
  exit 1
fi

if [[ $# -ge 2 ]]; then
  PARENT="$(realpath "$2")"
else
  PARENT="$HOME"
fi

mkdir -p "$PARENT"
echo "압축 해제: $ARCHIVE"
echo "대상 상위 디렉터리: $PARENT"
tar -xzf "$ARCHIVE" -C "$PARENT"
TOP="$(tar -tzf "$ARCHIVE" | head -1 | cut -d/ -f1)"
echo "완료. 예상 경로: $PARENT/$TOP"
if [[ -f "$PARENT/$TOP/.venv/bin/activate" ]]; then
  echo "가상환경 포함됨. 활성화: source $PARENT/$TOP/.venv/bin/activate"
else
  echo "가상환경이 없으면: cd $PARENT/$TOP && python3 -m venv .venv && .venv/bin/pip install -r rpi-eink-test/requirements.txt"
fi
