#!/usr/bin/env bash
# Thin compatibility entry point for the Python lint implementation.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/../python/cli.py" lint bare-grep-probe "$@"
