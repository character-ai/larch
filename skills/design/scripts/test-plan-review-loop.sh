#!/usr/bin/env bash
# Offline smoke tests for plan-review-loop.sh (extend with PATH stubs per #2676).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
PLR="$ROOT/skills/design/scripts/plan-review-loop.sh"

fail() { printf '%s\n' "$1" >&2; exit 1; }

bash -n "$PLR" || fail "bash -n plan-review-loop.sh failed"

set +e
"$PLR" --plan-file "$ROOT/README.md" --codex-present true --cursor-present true 2>/dev/null
rc=$?
set -e
[[ "$rc" == 2 ]] || fail "expected exit 2 when --design-tmpdir missing, got $rc"

# Do not invoke the full driver without PATH stubs — it runs scout/panel and can hang in CI.

printf '%s\n' "test-plan-review-loop: ok"
