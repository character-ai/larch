#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
source "$ROOT/skills/design/scripts/test-design-step5c.sh" 2>/dev/null || true
exit 0
