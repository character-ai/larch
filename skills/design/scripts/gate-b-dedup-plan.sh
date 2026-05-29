#!/usr/bin/env bash
# Mechanical Gate B post-apply dedup with optional-trailer preservation (issue #3175).
# Shared snapshot/validate helpers with plan-review-loop.sh.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$REPO_ROOT}"
if [[ ! -f "$PLUGIN_ROOT/scripts/lib-design-tmpdir.sh" ]]; then
    PLUGIN_ROOT="$REPO_ROOT"
fi
DEDUP_PLAN_LINES_PY="${LARCH_DEDUP_PLAN_LINES_PY:-$PLUGIN_ROOT/skills/design/scripts/dedup-plan-lines.py}"
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$PLUGIN_ROOT/scripts/lib-design-tmpdir.sh"
# shellcheck source=skills/design/scripts/lib-plan-optional-trailers.sh
source "$SCRIPT_DIR/lib-plan-optional-trailers.sh"

DESIGN_TMPDIR=""
MODE="dedup"
TRAILER_KEYS_FILE=""

usage() {
    cat <<'USAGE' >&2
usage: gate-b-dedup-plan.sh --design-tmpdir DIR [--snapshot-trailers | --dedup]
  --snapshot-trailers  Write optional trailer keys to .gate-b-optional-trailer-keys
  --dedup (default)    Run dedup-plan-lines.py and validate preserved keys
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir)
            DESIGN_TMPDIR="${2:?--design-tmpdir requires a value}"
            shift 2
            ;;
        --snapshot-trailers)
            MODE=snapshot
            shift
            ;;
        --dedup)
            MODE=dedup
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "gate-b-dedup-plan.sh: unknown argument: $1" >&2
            usage
            exit 3
            ;;
    esac
done

if [[ -z "$DESIGN_TMPDIR" ]]; then
    echo "gate-b-dedup-plan.sh: --design-tmpdir is required" >&2
    usage
    exit 3
fi

larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit 3

plan_path="$DESIGN_TMPDIR/plan.txt"
TRAILER_KEYS_FILE="$DESIGN_TMPDIR/.gate-b-optional-trailer-keys"

if [[ ! -f "$plan_path" ]]; then
    echo "gate-b-dedup-plan.sh: plan.txt missing under $DESIGN_TMPDIR" >&2
    exit 2
fi

if [[ "$MODE" == "snapshot" ]]; then
    snapshot_optional_trailer_keys "$plan_path" "$TRAILER_KEYS_FILE"
    exit 0
fi

if [[ ! -f "$TRAILER_KEYS_FILE" ]]; then
    echo "gate-b-dedup-plan.sh: --dedup requires prior --snapshot-trailers (.gate-b-optional-trailer-keys missing)" >&2
    exit 3
fi

if ! validate_optional_trailer_keys_preserved "$plan_path" "$TRAILER_KEYS_FILE"; then
    echo "gate-b-dedup-plan.sh: optional trailer keys lost before dedup" >&2
    exit 1
fi
snapshot_optional_trailer_values "$plan_path" "$(_optional_trailer_values_file "$TRAILER_KEYS_FILE")"

dedup_rc=0
dedup_plan_preserve_optional_trailers "$plan_path" "$TRAILER_KEYS_FILE" "$DESIGN_TMPDIR" "$DEDUP_PLAN_LINES_PY" || dedup_rc=$?
case "$dedup_rc" in
    0) exit 0 ;;
    1)
        echo "gate-b-dedup-plan.sh: optional trailer keys or values lost during dedup" >&2
        exit 1
        ;;
    *)
        echo "gate-b-dedup-plan.sh: dedup-plan-lines.py failed" >&2
        exit 2
        ;;
esac
