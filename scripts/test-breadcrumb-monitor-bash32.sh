#!/usr/bin/env bash
# test-breadcrumb-monitor-bash32.sh — run breadcrumb-monitor harness on macOS Bash 3.2.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

if [ ! -x /bin/bash ]; then
    echo "SKIP=no-bash32"
    exit 0
fi

version=$(/bin/bash --version 2>/dev/null | head -n 1 || true)
case "$version" in
    *"version 3.2"*) ;;
    *)
        echo "SKIP=no-bash32"
        exit 0
        ;;
esac

exec /bin/bash "$SCRIPT_DIR/test-breadcrumb-monitor.sh"
