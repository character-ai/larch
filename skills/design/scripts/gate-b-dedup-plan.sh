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

optional_keys_file="$TRAILER_KEYS_FILE"
if [[ ! -f "$optional_keys_file" ]]; then
    optional_keys_file=$(mktemp "$DESIGN_TMPDIR/.plan-optional-trailer-keys.XXXXXX")
    snapshot_optional_trailer_keys "$plan_path" "$optional_keys_file"
    _ephemeral_keys=1
else
    _ephemeral_keys=0
fi

pre_dedup_snapshot=""
if [[ -s "$optional_keys_file" ]]; then
    pre_dedup_snapshot=$(mktemp "$DESIGN_TMPDIR/.plan-pre-dedup.XXXXXX")
    cp -f "$plan_path" "$pre_dedup_snapshot"
fi

dedup_tmp=$(mktemp "$DESIGN_TMPDIR/.plan-dedup.XXXXXX")
if ! dedup_removed=$(python3 "$DEDUP_PLAN_LINES_PY" "$plan_path" "$dedup_tmp"); then
    rm -f "$dedup_tmp"
    [[ -n "$pre_dedup_snapshot" ]] && cp -f "$pre_dedup_snapshot" "$plan_path"
    rm -f "$pre_dedup_snapshot"
    [[ "$_ephemeral_keys" -eq 1 ]] && rm -f "$optional_keys_file"
    echo "gate-b-dedup-plan.sh: dedup-plan-lines.py failed" >&2
    exit 2
fi
if [[ ! "$dedup_removed" =~ ^[0-9]+$ ]]; then
    rm -f "$dedup_tmp"
    [[ -n "$pre_dedup_snapshot" ]] && cp -f "$pre_dedup_snapshot" "$plan_path"
    rm -f "$pre_dedup_snapshot"
    [[ "$_ephemeral_keys" -eq 1 ]] && rm -f "$optional_keys_file"
    echo "gate-b-dedup-plan.sh: dedup-plan-lines.py returned non-numeric count" >&2
    exit 2
fi
mv -f "$dedup_tmp" "$plan_path"
printf 'dedup-sweep: removed %s duplicate line(s) from plan.txt\n' "${dedup_removed:-0}"

if [[ -n "$pre_dedup_snapshot" ]] &&
    ! validate_optional_trailers_preserved "$plan_path" "$optional_keys_file"; then
    cp -f "$pre_dedup_snapshot" "$plan_path"
    rm -f "$pre_dedup_snapshot"
    [[ "$_ephemeral_keys" -eq 1 ]] && rm -f "$optional_keys_file"
    echo "gate-b-dedup-plan.sh: optional trailer keys lost during dedup" >&2
    exit 1
fi

rm -f "$pre_dedup_snapshot"
[[ "$_ephemeral_keys" -eq 1 ]] && rm -f "$optional_keys_file"
exit 0
