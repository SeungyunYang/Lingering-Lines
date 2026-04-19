#!/usr/bin/env bash
# 백업 스냅샷 목록 (최신이 위). 시점은 폴더명 snapshot-YYYYMMDD-HHMMSS 로 구분.
set -euo pipefail
ROOT="${BACKUP_ROOT:-$HOME/backups/lingering-lines}"
if [[ ! -d "$ROOT" ]]; then
  echo "백업 디렉터리 없음: $ROOT"
  exit 0
fi
echo "BACKUP_ROOT=$ROOT"
echo ""
ls -lt "$ROOT" 2>/dev/null || true
echo ""
for d in "$ROOT"/snapshot-*/; do
  [[ -d "$d" ]] || continue
  tgz="$(find "$d" -maxdepth 1 -name 'Lingering-Lines-*.tar.gz' -print -quit)"
  if [[ -n "$tgz" ]]; then
    echo "$(basename "$d")  →  $tgz"
  fi
done | sort -r
