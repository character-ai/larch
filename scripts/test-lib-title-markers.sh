#!/usr/bin/env bash
# Minimal regression for insert_signal_marker ([DESIGNED]/[DESIGNING] titles).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
# shellcheck source=scripts/lib-title-markers.sh
# shellcheck disable=SC1091
source "$ROOT/scripts/lib-title-markers.sh"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

got=$(insert_signal_marker '[DESIGNED] My feature' 'FALSE-POSITIVE')
[[ "$got" == '[DESIGNED] [FALSE-POSITIVE] My feature' ]] \
    || fail "expected [DESIGNED] [FALSE-POSITIVE] My feature, got: $got"

echo "ok: insert_signal_marker [DESIGNED] prefix"

got=$(insert_signal_marker '[DESIGNING] My feature' 'FALSE-POSITIVE')
[[ "$got" == '[DESIGNING] [FALSE-POSITIVE] My feature' ]] \
    || fail "expected [DESIGNING] [FALSE-POSITIVE] My feature, got: $got"

echo "ok: insert_signal_marker [DESIGNING] prefix"
