#!/usr/bin/env bash
# call-fixer.sh — Emit one accepted finding as structured fixer input.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: call-fixer.sh --finding-file FILE --finding-id FINDING_N --review-tmpdir DIR [--mark-applied|--mark-skipped REASON]"
}

FINDING_FILE=""
FINDING_ID=""
REVIEW_TMPDIR=""
MARK_APPLIED=false
MARK_SKIPPED_REASON=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --finding-file) FINDING_FILE="${2:?--finding-file requires a value}"; shift 2 ;;
        --finding-id) FINDING_ID="${2:?--finding-id requires a value}"; shift 2 ;;
        --review-tmpdir) REVIEW_TMPDIR="${2:?--review-tmpdir requires a value}"; shift 2 ;;
        --mark-applied) MARK_APPLIED=true; shift ;;
        --mark-skipped) MARK_SKIPPED_REASON="${2:?--mark-skipped requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "call-fixer.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -f "$FINDING_FILE" ]] || { larch_err "call-fixer.sh: --finding-file must name a file"; exit 2; }
[[ "$FINDING_ID" =~ ^FINDING_[0-9]+$ ]] || { larch_err "call-fixer.sh: --finding-id must look like FINDING_N"; exit 2; }
[[ -n "$REVIEW_TMPDIR" ]] || { larch_err "call-fixer.sh: --review-tmpdir is required"; exit 2; }
mkdir -p "$REVIEW_TMPDIR"

status_file="$REVIEW_TMPDIR/review-and-fix-status.env"
if [[ "$MARK_APPLIED" == "true" ]]; then
    printf '%s=%s\n' "$FINDING_ID" applied >> "$status_file"
    emit_kv FIXER_STATUS applied
    emit_kv FINDING_ID "$FINDING_ID"
    exit 0
fi
if [[ -n "$MARK_SKIPPED_REASON" ]]; then
    printf '%s=skipped:%s\n' "$FINDING_ID" "$MARK_SKIPPED_REASON" >> "$status_file"
    emit_kv FIXER_STATUS skipped
    emit_kv SKIP_REASON "$MARK_SKIPPED_REASON"
    emit_kv FINDING_ID "$FINDING_ID"
    exit 0
fi

block=$(awk -v id="$FINDING_ID" '
    $0 ~ "^### " id ":" { in_block=1; print; next }
    /^### FINDING_[0-9]+:/ && in_block { exit }
    in_block { print }
' "$FINDING_FILE")
[[ -n "$block" ]] || { larch_err "call-fixer.sh: finding id not found: $FINDING_ID"; exit 2; }

field_value() {
    local label="$1"
    printf '%s\n' "$block" | awk -v label="$label" '
        index($0, "- **" label "**:") == 1 {
            sub("^- \\*\\*" label "\\*\\*: ?", "")
            print
            exit
        }
    '
}

title=$(printf '%s\n' "$block" | sed -n "1s/^### ${FINDING_ID}: //p")
concern=$(field_value "Concern")
suggested=$(field_value "Suggested revision")
location=$(field_value "Location")
if [[ -z "$location" ]]; then
    location=$(field_value "File")
fi
if [[ -z "$location" ]]; then
    location=$(printf '%s\n' "$concern $suggested" | grep -Eo '([A-Za-z0-9._/-]+\.(sh|py|md|json|ts|tsx|js|jsx|yml|yaml|txt))' | head -1 || true)
fi

path_valid=false
path_reason="missing"
repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)
candidate="$location"
if [[ -n "$candidate" ]]; then
    case "$candidate" in
        /*) path_reason="absolute" ;;
        *..*) path_reason="contains-dotdot" ;;
        *$'\n'*|*$'\r'*|*$'\t'*) path_reason="control-character" ;;
        *)
            full="$repo_root/$candidate"
            if [[ -L "$full" ]]; then
                path_reason="symlink"
            elif [[ ! -e "$full" ]]; then
                path_reason="missing"
            else
                path_reason="ok"
                path_valid=true
                while IFS= read -r submodule_path; do
                    [[ -n "$submodule_path" ]] || continue
                    case "$candidate" in
                        "$submodule_path"|"$submodule_path"/*) path_valid=false; path_reason="submodule" ;;
                    esac
                done < <(git submodule status --recursive 2>/dev/null | awk '{print $2}')
            fi
            ;;
    esac
fi

emit_kv FIXER_STATUS ready
emit_kv FINDING_ID "$FINDING_ID"
emit_kv TITLE "$title"
emit_kv CONCERN "$concern"
emit_kv SUGGESTED_FIX "$suggested"
emit_kv FILE_PATH "$candidate"
emit_kv PATH_VALID "$path_valid"
emit_kv PATH_REASON "$path_reason"
