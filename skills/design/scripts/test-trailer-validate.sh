#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
# shellcheck source=skills/design/scripts/lib-plan-optional-trailers.sh
source "$SCRIPT_DIR/lib-plan-optional-trailers.sh"
P="${1:?plan}"; K="${2:?keys}"
if validate_optional_trailers_preserved "$P" "$K"; then
    echo validate=ok
    exit 0
fi
echo validate=fail
exit 1
