#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$TASK_ROOT"
cat docs/URUN_KONTROL_AJANI.md
printf '\n--- GUNCEL KONTROL DURUMU ---\n'
python3 scripts/product_review.py stats
printf '\n--- ILK BEKLEYEN URUN ---\n'
python3 scripts/product_review.py next --limit 1
