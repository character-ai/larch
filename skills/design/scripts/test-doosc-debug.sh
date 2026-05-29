#!/usr/bin/env bash
# Minimal reproducer for DOOSC cap-hit case (debug only).
set -euo pipefail
exec bash "$(dirname "$0")/test-plan-review-loop.sh" 2>&1 | awk '/^=== multi-round: cumulative accepted OOS/,/^=== multi-round: duplicate/ {print}'
