#!/usr/bin/env bash
# Offline regression for ship-pr run_rebase_rebump → Phase 1–4 (caller_kind=ship_pr_pre_push).
# Full scenarios live under scripts/test-ship-pr.sh --section phase14.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$REPO_ROOT/scripts/test-ship-pr.sh" --section phase14
