#!/usr/bin/env bash
# check-mid-run-dirty-tree.sh — Detect working-tree pollution during external agent runs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=scripts/lib-validate-meta-path.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-validate-meta-path.sh"

MODE=""
BASELINE=""
SIDECAR=""
PARSE_ERROR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode)
            if [[ $# -lt 2 ]]; then PARSE_ERROR="mode-missing-value"; break; fi
            MODE="$2"; shift 2 ;;
        --baseline)
            if [[ $# -lt 2 ]]; then PARSE_ERROR="baseline-missing-value"; break; fi
            BASELINE="$2"; shift 2 ;;
        --sidecar)
            if [[ $# -lt 2 ]]; then PARSE_ERROR="sidecar-missing-value"; break; fi
            SIDECAR="$2"; shift 2 ;;
        *)
            PARSE_ERROR="unknown-flag"; break ;;
    esac
done

if [[ -z "$MODE" ]]; then
    MODE="checkpoint"
    [[ -z "$PARSE_ERROR" ]] && PARSE_ERROR="mode-missing"
fi

case "$MODE" in
    baseline|checkpoint) ;;
    *) PARSE_ERROR="bad-mode"; MODE="checkpoint" ;;
esac

if [[ -n "$SIDECAR" ]]; then
    validate_meta_scalar_path --sidecar "$SIDECAR" >/dev/null 2>&1 || PARSE_ERROR="bad-sidecar-path"
fi
if [[ "$MODE" == "baseline" && -z "$BASELINE" && -z "$PARSE_ERROR" ]]; then
    PARSE_ERROR="baseline-required"
fi
if [[ -n "$BASELINE" ]]; then
    validate_meta_scalar_path --baseline "$BASELINE" >/dev/null 2>&1 || PARSE_ERROR="bad-baseline-path"
fi

TMPROOT="${TMPDIR:-/tmp}"
WORKDIR=$(mktemp -d "$TMPROOT/larch-mid-run-dirty-tree.XXXXXX" 2>/dev/null || mktemp -d "/tmp/larch-mid-run-dirty-tree.XXXXXX")
cleanup() {
    rm -rf "$WORKDIR"
}
trap cleanup EXIT

RESULT_FILE="$WORKDIR/result.env"
TRACKED_PATHS_FILE=""
NEW_UNTRACKED_PATHS_FILE=""

result_path_prefix() {
    if [[ -n "$SIDECAR" ]]; then
        printf '%s' "$SIDECAR"
    else
        printf '%s/larch-mid-run-dirty-tree.%s' "$TMPROOT" "$$"
    fi
}

file_nonempty() {
    [[ -s "$1" ]]
}

write_result_file() {
    local status="$1"
    local reason="${2:-}"
    local baseline_state="${3:-}"
    {
        printf 'STATUS=%s\n' "$status"
        printf 'MODE=%s\n' "$MODE"
        if [[ "$MODE" == "baseline" ]]; then
            printf 'UNTRACKED_BASELINE=%s\n' "$baseline_state"
        fi
        if [[ -n "$TRACKED_PATHS_FILE" ]]; then
            printf 'TRACKED_PATHS_FILE=%s\n' "$TRACKED_PATHS_FILE"
        fi
        if [[ -n "$NEW_UNTRACKED_PATHS_FILE" ]]; then
            printf 'NEW_UNTRACKED_PATHS_FILE=%s\n' "$NEW_UNTRACKED_PATHS_FILE"
        fi
        if [[ "$status" != "clean" || -n "$reason" ]]; then
            printf 'REASON=%s\n' "${reason:-unknown}"
        fi
    } > "$RESULT_FILE"
}

publish_result() {
    cat "$RESULT_FILE"
    if [[ -n "$SIDECAR" ]]; then
        local tmp="${SIDECAR}.tmp.$$"
        cp "$RESULT_FILE" "$tmp" 2>/dev/null && mv -f "$tmp" "$SIDECAR" 2>/dev/null || rm -f "$tmp" 2>/dev/null || true
    fi
}

emit_unknown() {
    local reason="$1"
    local baseline_state="${2:-missing}"
    write_result_file unknown "$reason" "$baseline_state"
    publish_result
    exit 0
}

if [[ -n "$PARSE_ERROR" ]]; then
    emit_unknown "$PARSE_ERROR" "missing"
fi

STATUS_OUT="$WORKDIR/status.out"
if ! git status --porcelain > "$STATUS_OUT" 2>/dev/null; then
    emit_unknown "git-status-failed" "missing"
fi

if [[ "$MODE" == "checkpoint" ]]; then
    if [[ -s "$STATUS_OUT" ]]; then
        write_result_file dirty "checkpoint-dirty" ""
    else
        write_result_file clean "" ""
    fi
    publish_result
    exit 0
fi

UNSTAGED="$WORKDIR/unstaged.z"
STAGED="$WORKDIR/staged.z"
TRACKED="$WORKDIR/tracked.z"
CURRENT_UNTRACKED="$WORKDIR/current-untracked.z"
BASELINE_SORTED="$WORKDIR/baseline.z"
UNTRACKED_DELTA="$WORKDIR/untracked-delta.z"

if ! git diff --name-only -z > "$UNSTAGED" 2>/dev/null; then
    emit_unknown "git-diff-failed" "missing"
fi
if ! git diff --name-only --cached -z > "$STAGED" 2>/dev/null; then
    emit_unknown "git-diff-cached-failed" "missing"
fi
# Guard the merge+sort pipeline so any cat / sort / pipe failure (disk
# full, sort OOM, I/O error) still publishes STATUS=unknown via
# emit_unknown instead of aborting under `set -euo pipefail` and
# violating the "always exits 0" contract documented in
# scripts/check-mid-run-dirty-tree.md.
if ! { cat "$UNSTAGED" "$STAGED" | LC_ALL=C sort -zu > "$TRACKED"; }; then
    emit_unknown "tracked-merge-sort-failed" "missing"
fi

if ! git ls-files --others --exclude-standard -z > "$CURRENT_UNTRACKED" 2>/dev/null; then
    emit_unknown "git-ls-files-failed" "missing"
fi
if ! LC_ALL=C sort -zu "$CURRENT_UNTRACKED" -o "$CURRENT_UNTRACKED"; then
    emit_unknown "untracked-sort-failed" "missing"
fi

BASELINE_STATE="missing"
if [[ -r "$BASELINE" ]]; then
    BASELINE_STATE="present"
    if ! LC_ALL=C sort -zu "$BASELINE" -o "$BASELINE_SORTED"; then
        emit_unknown "baseline-sort-failed" "$BASELINE_STATE"
    fi
    LC_ALL=C perl -0ne '
        BEGIN {
            open my $baseline, "<", $ARGV[0] or exit 3;
            local $/ = "\0";
            while (defined(my $path = <$baseline>)) {
                chomp $path;
                $seen{$path} = 1 if length $path;
            }
            close $baseline;
            shift @ARGV;
            local $/ = "\0";
        }
        chomp;
        print "$_\0" if length($_) && !$seen{$_};
    ' "$BASELINE_SORTED" "$CURRENT_UNTRACKED" > "$UNTRACKED_DELTA" || emit_unknown "untracked-delta-failed" "$BASELINE_STATE"
else
    : > "$UNTRACKED_DELTA"
fi

PREFIX=$(result_path_prefix)
if file_nonempty "$TRACKED"; then
    TRACKED_PATHS_FILE="${PREFIX}.tracked-paths"
    cp "$TRACKED" "$TRACKED_PATHS_FILE" 2>/dev/null || emit_unknown "tracked-paths-write-failed" "$BASELINE_STATE"
fi

if [[ "$BASELINE_STATE" == "present" && -s "$UNTRACKED_DELTA" ]]; then
    NEW_UNTRACKED_PATHS_FILE="${PREFIX}.new-untracked-paths"
    cp "$UNTRACKED_DELTA" "$NEW_UNTRACKED_PATHS_FILE" 2>/dev/null || emit_unknown "new-untracked-paths-write-failed" "$BASELINE_STATE"
fi

if [[ "$BASELINE_STATE" == "missing" && -s "$CURRENT_UNTRACKED" ]]; then
    emit_unknown "baseline-missing-untracked-ambiguous" "$BASELINE_STATE"
fi

if [[ -n "$TRACKED_PATHS_FILE" || -n "$NEW_UNTRACKED_PATHS_FILE" ]]; then
    write_result_file dirty "working-tree-dirty" "$BASELINE_STATE"
else
    write_result_file clean "" "$BASELINE_STATE"
fi
publish_result
