#!/usr/bin/env bash
# test-classify-bump.sh — Offline harness for classify-bump.sh idempotency edges.
# Delegates to .claude/skills/bump-version/scripts/test-classify-bump.sh.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/../.claude/skills/bump-version/scripts/test-classify-bump.sh" "$@"
