#!/usr/bin/env bash
# snapshot-plan-round.sh — write-once plan snapshots and round cursor for /design assessor.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$PLUGIN_ROOT/scripts/lib-design-tmpdir.sh"

DESIGN_TMPDIR=""
SUBCMD=""
ROUND=""
CURSOR_VALUE=""

usage() {
    larch_err "Usage: snapshot-plan-round.sh write-original|write-after|read-cursor|write-cursor|revert-round --design-tmpdir DIR [--round N] [--value N]"
}

atomic_copy_plan() {
    local src="$1" dest="$2" prefix="$3"
    local tmp
    tmp=$(mktemp "$DESIGN_TMPDIR/${prefix}.XXXXXX")
    if ! cp -p "$src" "$tmp"; then
        rm -f "$tmp"
        return 1
    fi
    if ! mv -f "$tmp" "$dest"; then
        rm -f "$tmp"
        return 1
    fi
}

parse_cursor_file() {
    local file="$1" raw reason="malformed"
    if [[ ! -f "$file" ]]; then
        printf '1'
        return 0
    fi
    IFS= read -r raw <"$file" || raw=""
    case "$raw" in
        ''|*[!0-9]*|0|-*)
            larch_errf '**⚠ snapshot-plan-round: cursor file %s; defaulting to 1**\n' "$reason"
            printf '1'
            ;;
        *)
            printf '%s' "$((10#$raw))"
            ;;
    esac
}

restore_review_artifacts_after_revert() {
    local round="$1" prev_round prev_dir
    prev_round=$((round - 1))
    prev_dir="$DESIGN_TMPDIR/plan-review/round-${prev_round}"
    local name src
    for name in \
        accepted-plan-findings.md rejected-findings.md oos.md oos-this-round.md \
        oos-accepted-design.md voting-tally.md ballot.txt findings.md \
        findings-in-scope.md findings-in-scope.pre-dedup.md findings-oos.md \
        findings-oos.pre-dedup.md findings-classification.tsv; do
        src="$prev_dir/$name"
        if (( prev_round > 0 )) && [[ -f "$src" && ! -L "$src" ]]; then
            cp -f "$src" "$DESIGN_TMPDIR/$name"
        else
            rm -f "$DESIGN_TMPDIR/$name"
        fi
    done
    rm -rf "$DESIGN_TMPDIR/plan-review/round-${round}"
    rm -f \
        "$DESIGN_TMPDIR/assessor-verdict-round-${round}.txt" \
        "$DESIGN_TMPDIR/assessor-verdict-round-${round}.txt.env" \
        "$DESIGN_TMPDIR/claude-plan-assessor-round-${round}.txt" \
        "$DESIGN_TMPDIR/claude-plan-assessor-round-${round}.txt.meta" \
        "$DESIGN_TMPDIR/claude-plan-assessor-round-${round}.txt.done" \
        "$DESIGN_TMPDIR/codex-plan-assessor-round-${round}.txt" \
        "$DESIGN_TMPDIR/codex-plan-assessor-round-${round}.txt.diag" \
        "$DESIGN_TMPDIR/codex-plan-assessor-round-${round}.txt.json" \
        "$DESIGN_TMPDIR/codex-plan-assessor-round-${round}.txt.meta" \
        "$DESIGN_TMPDIR/cursor-plan-assessor-round-${round}.txt" \
        "$DESIGN_TMPDIR/cursor-plan-assessor-round-${round}.txt.diag" \
        "$DESIGN_TMPDIR/cursor-plan-assessor-round-${round}.txt.json" \
        "$DESIGN_TMPDIR/cursor-plan-assessor-round-${round}.txt.meta"
}

clear_post_revert_state() {
    rm -f \
        "$DESIGN_TMPDIR/.design-postplan-emit-result.env" \
        "$DESIGN_TMPDIR/.gate-b-optional-trailer-keys" \
        "$DESIGN_TMPDIR/.gate-b-optional-trailer-keys.values" \
        "$DESIGN_TMPDIR/validate-plan-commands.log" \
        "$DESIGN_TMPDIR/check-plan-size.validation.log" \
        "$DESIGN_TMPDIR/.step3-entry-plan-printed"
    rm -f "$DESIGN_TMPDIR"/.plan-command-autofix-*.attempted
    rm -f \
        "$DESIGN_TMPDIR/.completed/finalize" \
        "$DESIGN_TMPDIR/.completed/step-3b" \
        "$DESIGN_TMPDIR/.completed/step-4" \
        "$DESIGN_TMPDIR/.completed/step-4b" \
        "$DESIGN_TMPDIR/.completed/step-5b" \
        "$DESIGN_TMPDIR/.completed/step-5c" \
        "$DESIGN_TMPDIR/.completed/step-5d" \
        "$DESIGN_TMPDIR/.completed/step-6"
    if diff_line=$(awk -F': *' '$1=="diff_lines"{value=$2} END{if (value ~ /^[0-9]+$/) print value}' "$DESIGN_TMPDIR/plan.txt"); then
        if [[ -n "$diff_line" ]]; then
            printf '%s\n' "$diff_line" >"$DESIGN_TMPDIR/diff-lines.txt"
        else
            rm -f "$DESIGN_TMPDIR/diff-lines.txt"
        fi
    else
        rm -f "$DESIGN_TMPDIR/diff-lines.txt"
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        write-original|write-after|read-cursor|write-cursor|revert-round)
            SUBCMD="$1"
            shift
            ;;
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --round) ROUND="${2:?}"; shift 2 ;;
        --value) CURSOR_VALUE="${2:?}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) larch_err "snapshot-plan-round.sh: unknown argument: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$SUBCMD" ]] || { usage; exit 2; }
[[ -n "$DESIGN_TMPDIR" ]] || { larch_err "snapshot-plan-round.sh: --design-tmpdir is required"; exit 2; }
larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit $?
mkdir -p "$DESIGN_TMPDIR"

case "$SUBCMD" in
    write-original)
        src="$DESIGN_TMPDIR/plan.txt"
        dest="$DESIGN_TMPDIR/plan.txt-original"
        [[ -f "$src" ]] || { larch_err "snapshot-plan-round.sh: plan.txt missing"; exit 2; }
        if [[ -e "$dest" ]]; then
            emit "⏩ snapshot-plan-round: original already exists; preserved"
            exit 0
        fi
        atomic_copy_plan "$src" "$dest" ".snapshot-original"
        ;;
    write-after)
        [[ -n "$ROUND" ]] || { larch_err "snapshot-plan-round.sh: write-after requires --round"; exit 2; }
        case "$ROUND" in ''|*[!0-9]*|0) larch_err "snapshot-plan-round.sh: --round must be a positive integer"; exit 2 ;; esac
        ROUND=$((10#$ROUND))
        src="$DESIGN_TMPDIR/plan.txt"
        dest="$DESIGN_TMPDIR/plan-after-round-${ROUND}.txt"
        [[ -f "$src" ]] || { larch_err "snapshot-plan-round.sh: plan.txt missing"; exit 2; }
        if [[ -e "$dest" ]]; then
            emit "⏩ snapshot-plan-round: plan-after-round-${ROUND} already exists; preserved"
            exit 0
        fi
        atomic_copy_plan "$src" "$dest" ".snapshot-after"
        ;;
    read-cursor)
        cursor_file="$DESIGN_TMPDIR/plan-review-round-cursor.txt"
        n=$(parse_cursor_file "$cursor_file")
        emit_kv ROUND_CURSOR "$n"
        ;;
    write-cursor)
        [[ -n "$CURSOR_VALUE" ]] || { larch_err "snapshot-plan-round.sh: write-cursor requires --value"; exit 2; }
        case "$CURSOR_VALUE" in ''|*[!0-9]*|0) larch_err "snapshot-plan-round.sh: --value must be a positive integer"; exit 2 ;; esac
        CURSOR_VALUE=$((10#$CURSOR_VALUE))
        cursor_file="$DESIGN_TMPDIR/plan-review-round-cursor.txt"
        tmp=$(mktemp "$DESIGN_TMPDIR/.cursor.XXXXXX")
        printf '%s\n' "$CURSOR_VALUE" >"$tmp"
        mv -f "$tmp" "$cursor_file"
        ;;
    revert-round)
        # Roll back round N's applied findings: restore plan.txt to the pre-round
        # snapshot, drop round N's post-Gate-B snapshot, and roll the cursor +
        # review-round counter back (mirrors the write-after-failed rollback:
        # cursor=N, count=N-1). The assessor is HARD-only, so plan.txt-original
        # exists for the round-1 baseline.
        [[ -n "$ROUND" ]] || { larch_err "snapshot-plan-round.sh: revert-round requires --round"; exit 2; }
        case "$ROUND" in ''|*[!0-9]*|0) larch_err "snapshot-plan-round.sh: --round must be a positive integer"; exit 2 ;; esac
        ROUND=$((10#$ROUND))
        if [[ "$ROUND" -gt 1 ]]; then
            restore_src="$DESIGN_TMPDIR/plan-after-round-$((ROUND - 1)).txt"
        else
            restore_src="$DESIGN_TMPDIR/plan.txt-original"
        fi
        [[ -f "$restore_src" && ! -L "$restore_src" ]] || { larch_err "snapshot-plan-round.sh: revert-round source missing or unsafe: ${restore_src##*/}"; exit 2; }
        atomic_copy_plan "$restore_src" "$DESIGN_TMPDIR/plan.txt" ".revert-plan" \
            || { larch_err "snapshot-plan-round.sh: revert-round copy-back failed"; exit 1; }
        rm -f "$DESIGN_TMPDIR/plan-after-round-${ROUND}.txt"
        restore_review_artifacts_after_revert "$ROUND"
        clear_post_revert_state
        printf '%s\n' "$((ROUND - 1))" >"$DESIGN_TMPDIR/review-round-count.txt"
        cursor_file="$DESIGN_TMPDIR/plan-review-round-cursor.txt"
        tmp=$(mktemp "$DESIGN_TMPDIR/.cursor.XXXXXX")
        printf '%s\n' "$ROUND" >"$tmp"
        mv -f "$tmp" "$cursor_file"
        emit_kv REVERT_STATUS ok
        emit_kv RESTORED_FROM "${restore_src##*/}"
        emit_kv CURSOR "$ROUND"
        emit_kv REVIEW_ROUND_COUNT "$((ROUND - 1))"
        ;;
    *)
        usage
        exit 2
        ;;
esac

exit 0
