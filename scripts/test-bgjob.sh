#!/usr/bin/env bash
# test-bgjob.sh — regression harness for bgjob start/wait/reap coverage.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

cd "$REPO_ROOT"
python3 -m pytest python/tests/bgjob -q
