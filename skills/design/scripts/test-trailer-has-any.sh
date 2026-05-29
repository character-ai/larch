#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
# shellcheck source=skills/design/scripts/lib-plan-optional-trailers.sh
source "$SCRIPT_DIR/lib-plan-optional-trailers.sh"
P="${1:?plan path}"
if plan_has_any_optional_trailer "$P"; then
    echo has_any=yes
    exit 0
fi
echo has_any=no
exit 1
