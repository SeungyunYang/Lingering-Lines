#!/usr/bin/env bash
# Lingering-Lines 전체 스냅샷 (코드, .venv, .git 포함 가능) + 메타데이터.
# 기본 출력: ~/backups/lingering-lines/
#
# 사용법:
#   ./scripts/backup_lingering_lines.sh
#   ./scripts/backup_lingering_lines.sh --no-venv          # 가상환경 제외(용량↓, 복원 시 pip로 재설치)
#   BACKUP_ROOT=/mnt/usb/backup ./scripts/backup_lingering_lines.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/backups/lingering-lines}"
INCLUDE_VENV=1
DRY_RUN=0

usage() {
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-venv) INCLUDE_VENV=0 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "알 수 없는 인자: $1" >&2; usage; exit 1 ;;
  esac
  shift
done

TS="$(date +%Y%m%d-%H%M%S)"
NAME="$(basename "$REPO_ROOT")"
PARENT="$(dirname "$REPO_ROOT")"
DEST_DIR="$BACKUP_ROOT/snapshot-$TS"
ARCHIVE="$DEST_DIR/${NAME}-${TS}.tar.gz"
MANIFEST="$DEST_DIR/MANIFEST.txt"

mkdir -p "$DEST_DIR"

{
  echo "=== Lingering-Lines backup manifest ==="
  echo "created_utc: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "host: $(hostname -f 2>/dev/null || hostname)"
  echo "uname: $(uname -a)"
  echo "repo: $REPO_ROOT"
  echo "include_venv: $INCLUDE_VENV"
  echo ""
  if [[ -d "$REPO_ROOT/.git" ]]; then
    echo "--- git ---"
    (cd "$REPO_ROOT" && git rev-parse HEAD 2>/dev/null || echo "(no HEAD)")
    (cd "$REPO_ROOT" && git branch -v 2>/dev/null | head -20 || true)
    (cd "$REPO_ROOT" && git status -sb 2>/dev/null || true)
    echo ""
  fi
  echo "--- python ---"
  command -v python3 >/dev/null && python3 --version || echo "python3 없음"
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    echo "venv_python: $($REPO_ROOT/.venv/bin/python --version 2>&1)"
    echo ""
    echo "--- pip freeze (.venv) ---"
    "$REPO_ROOT/.venv/bin/pip" freeze 2>/dev/null || true
  else
    echo "( .venv 없음 또는 실행 불가 )"
  fi
} > "$MANIFEST"

FREEZE_FILE="$DEST_DIR/pip-freeze-${TS}.txt"
if [[ -x "$REPO_ROOT/.venv/bin/pip" ]]; then
  "$REPO_ROOT/.venv/bin/pip" freeze > "$FREEZE_FILE" 2>/dev/null || rm -f "$FREEZE_FILE"
else
  echo "(pip freeze 생략: .venv 없음)" > "$FREEZE_FILE"
fi

EXCLUDES=(
  --exclude="$NAME/__pycache__"
  --exclude="$NAME/*/__pycache__"
  --exclude="$NAME/*/*/__pycache__"
  --exclude="$NAME/.mypy_cache"
  --exclude="$NAME/.pytest_cache"
)
if [[ "$INCLUDE_VENV" -eq 0 ]]; then
  EXCLUDES+=(--exclude="$NAME/.venv")
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] tar 생성 생략"
  echo "MANIFEST: $MANIFEST"
  exit 0
fi

tar -C "$PARENT" -czf "$ARCHIVE" "${EXCLUDES[@]}" "$NAME"

BYTES="$(stat -c%s "$ARCHIVE" 2>/dev/null || wc -c <"$ARCHIVE")"
echo ""
echo "백업 완료"
echo "  아카이브: $ARCHIVE"
echo "  크기:     $BYTES bytes"
echo "  매니페스트: $MANIFEST"
echo "  pip 목록:   $FREEZE_FILE"
echo ""
echo "복원 예:  bash $REPO_ROOT/scripts/restore_lingering_lines.sh \"$ARCHIVE\""
