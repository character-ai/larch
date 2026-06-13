#!/usr/bin/env bash
# Mechanical Gate B post-apply dedup with optional-trailer preservation (issue #3175).

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

optional_cli() {
    python3 "$PLUGIN_ROOT/python/cli.py" plan optional-trailers "$@"
}

if [[ "$MODE" == "snapshot" ]]; then
    optional_cli snapshot-keys --plan-file "$plan_path" --output "$TRAILER_KEYS_FILE"
    optional_cli snapshot-values --plan-file "$plan_path" --output "$TRAILER_KEYS_FILE.values"
    exit 0
fi

if [[ ! -f "$TRAILER_KEYS_FILE" ]]; then
    echo "gate-b-dedup-plan.sh: --dedup requires prior --snapshot-trailers (.gate-b-optional-trailer-keys missing)" >&2
    exit 3
fi

if ! optional_cli validate-keys --plan-file "$plan_path" --keys-file "$TRAILER_KEYS_FILE"; then
    echo "gate-b-dedup-plan.sh: optional trailer keys lost before dedup" >&2
    exit 1
fi
optional_cli snapshot-values --plan-file "$plan_path" --output "$TRAILER_KEYS_FILE.values"

pre_dedup_snapshot=""
if [[ -s "$TRAILER_KEYS_FILE" ]]; then
    pre_dedup_snapshot=$(mktemp "$DESIGN_TMPDIR/.plan-pre-dedup.XXXXXX")
    cp -f "$plan_path" "$pre_dedup_snapshot"
fi

dedup_tmp=$(mktemp "$DESIGN_TMPDIR/.plan-dedup.XXXXXX")
dedup_removed=""
if ! dedup_removed=$(python3 "$DEDUP_PLAN_LINES_PY" "$plan_path" "$dedup_tmp"); then
    rm -f "$dedup_tmp"
    if [[ -n "$pre_dedup_snapshot" ]]; then
        cp -f "$pre_dedup_snapshot" "$plan_path"
    fi
    rm -f "$pre_dedup_snapshot"
    echo "gate-b-dedup-plan.sh: dedup-plan-lines.py failed" >&2
    exit 2
fi
if [[ ! "$dedup_removed" =~ ^[0-9]+$ ]]; then
    rm -f "$dedup_tmp"
    if [[ -n "$pre_dedup_snapshot" ]]; then
        cp -f "$pre_dedup_snapshot" "$plan_path"
    fi
    rm -f "$pre_dedup_snapshot"
    echo "gate-b-dedup-plan.sh: dedup-plan-lines.py failed" >&2
    exit 2
fi
mv -f "$dedup_tmp" "$plan_path"
printf 'dedup-sweep: removed %s duplicate line(s) from plan.txt\n' "${dedup_removed:-0}"

if ! optional_cli validate-values --plan-file "$plan_path" --values-file "$TRAILER_KEYS_FILE.values"; then
    if [[ -n "$pre_dedup_snapshot" ]]; then
        cp -f "$pre_dedup_snapshot" "$plan_path"
    fi
    rm -f "$pre_dedup_snapshot"
    echo "gate-b-dedup-plan.sh: optional trailer keys or values lost during dedup" >&2
    exit 1
fi

rm -f "$pre_dedup_snapshot"
exit 0
