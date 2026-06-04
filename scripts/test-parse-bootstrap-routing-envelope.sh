#!/usr/bin/env bash
# test-parse-bootstrap-routing-envelope.sh — set -e regression for routing parse fallback.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$ROOT/scripts/parse-bootstrap-routing-envelope.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-parse-bootstrap.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

run_case() {
    mode=$1
    tmpdir="$TMPROOT/$mode"
    mkdir -p "$tmpdir"
    cat >"$tmpdir/bootstrap-routing.env" <<ENV
IMPLEMENT_TMPDIR=$tmpdir
PLAN_FILE=/tmp/from-file-plan.txt
coder=codex
RUN_ID=run-from-file
BRANCH_NAME=branch-from-file
ENV
    if [ "$mode" = preserve ]; then
        coder=operator-choice
        coder_fallback=operator-fallback
    fi
    _inv_out="IMPLEMENT_TMPDIR=$tmpdir
PLAN_FILE=/tmp/from-stdout-plan.txt
coder=claude
coder_fallback=codex
RUN_ID=run-from-stdout
BRANCH_NAME=branch-from-stdout"
    set -euo pipefail
    if [ "$mode" = preserve ]; then
        set -- --preserve-coder
    else
        set --
    fi
    # shellcheck disable=SC1090
    . "$SCRIPT" "$@"
    [ "$IMPLEMENT_TMPDIR" = "$tmpdir" ]
    [ "$PLAN_FILE" = /tmp/from-file-plan.txt ]
    [ "$RUN_ID" = run-from-file ]
    [ "$BRANCH_NAME" = branch-from-file ]
    if [ "$mode" = preserve ]; then
        [ "${coder:-}" = operator-choice ]
        [ "${coder_fallback:-}" = operator-fallback ]
    else
        [ "${coder:-}" = codex ]
        [ "${coder_fallback:-}" = codex ]
    fi
}

run_case default
run_case preserve

echo "test-parse-bootstrap-routing-envelope: ok"
