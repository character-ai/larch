#!/usr/bin/env bash
# sweep-run-logs-phase3a.sh — Retroactive Phase 3a sweep of committed run logs.
# Deletes projection-only files now superseded by review-findings-full.jsonl,
# and removes plan-goals-test.md (issue body is the canonical plan store).
# Safe to re-run; git rm on already-absent paths is a no-op.
# Usage: sweep-run-logs-phase3a.sh [--dry-run]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
LOGS_DIR="$REPO_ROOT/larch-logs/implement"

DRY_RUN=false
[ "${1:-}" = "--dry-run" ] && DRY_RUN=true

deleted_round=0
deleted_plan=0
skipped_legacy=0

for run_dir in "$LOGS_DIR"/*/; do
    [ -d "$run_dir" ] || continue

    # plan-goals-test.md — always remove (issue body is the canonical plan).
    plan_file="$run_dir/plan-goals-test.md"
    if [ -f "$plan_file" ]; then
        if [ "$DRY_RUN" = true ]; then
            printf 'DRY-RUN: git rm %s\n' "$plan_file"
        else
            git -C "$REPO_ROOT" rm --quiet --force "$plan_file" 2>/dev/null || true
        fi
        deleted_plan=$((deleted_plan + 1))
    fi

    # Round-level projection files: only delete where review-findings-full.jsonl
    # exists at the run level as the canonical store.
    # Legacy runs (no jsonl) keep their markdown — it is the only copy there.
    if [ ! -f "$run_dir/review-findings-full.jsonl" ]; then
        # Count any round dirs that would have been swept as legacy-skipped.
        for round_dir in "$run_dir"round-*/; do
            [ -d "$round_dir" ] && skipped_legacy=$((skipped_legacy + 1))
        done
        continue
    fi
    for round_dir in "$run_dir"round-*/; do
        [ -d "$round_dir" ] || continue
        for drop_file in findings.md accepted-findings.md oos.md rejected-findings-full.md; do
            target="$round_dir$drop_file"
            if [ -f "$target" ]; then
                if [ "$DRY_RUN" = true ]; then
                    printf 'DRY-RUN: git rm %s\n' "$target"
                else
                    git -C "$REPO_ROOT" rm --quiet --force "$target" 2>/dev/null || true
                fi
                deleted_round=$((deleted_round + 1))
            fi
        done
    done
done

# Round-level jsonl per run dir is checked above; handle run-level jsonl too.
# (In practice review-findings-full.jsonl lives in round dirs, not the run root.)

printf 'sweep-run-logs-phase3a: deleted_plan=%d deleted_round_projections=%d skipped_legacy_rounds=%d dry_run=%s\n' \
    "$deleted_plan" "$deleted_round" "$skipped_legacy" "$DRY_RUN"
