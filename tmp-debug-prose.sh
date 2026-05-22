#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$REPO_ROOT/scripts/test-implement-admission.sh" 2>/dev/null || true
