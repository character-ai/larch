#!/usr/bin/env bash
# retro-sweep-design-logs-phase3d.sh — apply Phase 3d cuts to committed design logs.
#
# Cut 1: delete round-level accepted-plan-findings.md / rejected-findings.md when
#         the round copy is a prefix-subset of the top-level cumulative file.
# Cut 2: delete GitHub-redundant top-level files: issue-body.txt, issue.json,
#         architecture-diagram.md.
#
# Run from the repository root. Skips any run dir containing pause-state.txt.
# Exits non-zero on argument error; proceeds best-effort for individual run dirs.
#
# Usage:
#   scripts/retro-sweep-design-logs-phase3d.sh [--dry-run] [--design-logs-root PATH]
#
# Defaults to larch-logs/design/ relative to the repo root.

set -euo pipefail

DRY_RUN=false
DESIGN_LOGS_ROOT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; shift ;;
        --design-logs-root) DESIGN_LOGS_ROOT="${2:?--design-logs-root requires a value}"; shift 2 ;;
        -h|--help)
            printf 'Usage: %s [--dry-run] [--design-logs-root PATH]\n' "$(basename "$0")" >&2
            exit 0
            ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 1 ;;
    esac
done

REPO_ROOT="$(git rev-parse --show-toplevel)"
if [[ -z "$DESIGN_LOGS_ROOT" ]]; then
    DESIGN_LOGS_ROOT="$REPO_ROOT/larch-logs/design"
fi

if [[ ! -d "$DESIGN_LOGS_ROOT" ]]; then
    printf 'design-logs root not found: %s\n' "$DESIGN_LOGS_ROOT" >&2
    exit 1
fi

deleted_cut1=0
kept_cut1=0
deleted_cut2=0
skipped_paused=0

# is_prefix_subset FILE_A FILE_B — returns 0 when every line of FILE_A appears
# as a leading prefix in FILE_B (i.e. FILE_B contains FILE_A's content as a
# contiguous prefix or is byte-identical).  Returns 1 otherwise.
is_prefix_subset() {
    local a="$1" b="$2"
    local a_lines b_lines
    a_lines=$(wc -l <"$a" 2>/dev/null || printf '0')
    b_lines=$(wc -l <"$b" 2>/dev/null || printf '0')
    # A must be no longer than B.
    [[ "$a_lines" -le "$b_lines" ]] || return 1
    # The first a_lines lines of B must equal A.
    local a_content b_prefix
    a_content=$(cat "$a")
    b_prefix=$(head -n "$a_lines" "$b")
    [[ "$a_content" == "$b_prefix" ]]
}

while IFS= read -r -d '' run_dir; do
    run_id=$(basename "$run_dir")

    # Skip paused runs.
    if [[ -f "$run_dir/pause-state.txt" ]]; then
        printf 'skip (paused): %s\n' "$run_id"
        skipped_paused=$((skipped_paused + 1))
        continue
    fi

    # Cut 2: delete GitHub-redundant top-level snapshots.
    for f in issue-body.txt issue.json architecture-diagram.md; do
        target="$run_dir/$f"
        if [[ -f "$target" ]]; then
            if [[ "$DRY_RUN" == "true" ]]; then
                printf 'would delete (cut2): %s/%s\n' "$run_id" "$f"
            else
                git -C "$REPO_ROOT" rm -f -- "$target" >/dev/null 2>&1 || rm -f "$target"
                printf 'deleted (cut2): %s/%s\n' "$run_id" "$f"
            fi
            deleted_cut2=$((deleted_cut2 + 1))
        fi
    done

    # Cut 1: delete round-level cumulative files when they are prefix-subsets
    # of the top-level canonical copy.
    plan_review="$run_dir/plan-review"

    if [[ -d "$plan_review" ]]; then
        while IFS= read -r -d '' round_dir; do
            for basename in accepted-plan-findings.md rejected-findings.md; do
                round_copy="$round_dir/$basename"
                [[ -f "$round_copy" ]] || continue
                top_copy="$run_dir/$basename"
                if [[ ! -f "$top_copy" ]]; then
                    printf 'keep (no top-level copy): %s/plan-review/%s/%s\n' \
                        "$run_id" "$(basename "$round_dir")" "$basename"
                    kept_cut1=$((kept_cut1 + 1))
                    continue
                fi
                if is_prefix_subset "$round_copy" "$top_copy"; then
                    if [[ "$DRY_RUN" == "true" ]]; then
                        printf 'would delete (cut1): %s/plan-review/%s/%s\n' \
                            "$run_id" "$(basename "$round_dir")" "$basename"
                    else
                        git -C "$REPO_ROOT" rm -f -- "$round_copy" >/dev/null 2>&1 || rm -f "$round_copy"
                        printf 'deleted (cut1): %s/plan-review/%s/%s\n' \
                            "$run_id" "$(basename "$round_dir")" "$basename"
                    fi
                    deleted_cut1=$((deleted_cut1 + 1))
                else
                    printf 'keep (not a prefix-subset): %s/plan-review/%s/%s\n' \
                        "$run_id" "$(basename "$round_dir")" "$basename"
                    kept_cut1=$((kept_cut1 + 1))
                fi
            done
        done < <(find "$plan_review" -maxdepth 1 -type d -name 'round-*' -print0 | sort -z)
    fi
done < <(find "$DESIGN_LOGS_ROOT" -maxdepth 1 -mindepth 1 -type d -print0 | sort -z)

printf '\nSummary:\n'
printf '  Cut 1 deleted: %d  kept: %d\n' "$deleted_cut1" "$kept_cut1"
printf '  Cut 2 deleted: %d\n' "$deleted_cut2"
printf '  Paused dirs skipped: %d\n' "$skipped_paused"
if [[ "$DRY_RUN" == "true" ]]; then
    printf '  (dry-run — no files removed)\n'
fi
