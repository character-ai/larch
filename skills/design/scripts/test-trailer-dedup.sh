#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
# shellcheck source=skills/design/scripts/lib-plan-optional-trailers.sh
source "$SCRIPT_DIR/lib-plan-optional-trailers.sh"
D="${1:?dir}"
P="$D/plan.txt"
K="$D/.gate-b-optional-trailer-keys"
if dedup_plan_preserve_optional_trailers "$P" "$K" "$D" "$SCRIPT_DIR/dedup-plan-lines.py"; then
    echo dedup=ok
    exit 0
fi
echo dedup=fail rc=$?
exit 1
