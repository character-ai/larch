#!/usr/bin/env bash
# Shared per-round forensic artifact allowlist for plan-review-loop.sh and design-log-publish.sh.

# Return 0 when basename is included in plan-review/round-N/ staging; 1 when excluded.
design_round_artifact_included() {
    local name="$1"
    case "$name" in
        cursor-plan-*-output.txt|codex-primary-plan-*-output.txt|dyn-*-output.txt)
            return 1
            ;;
        # #3713: preserve the composed vendor-failure carrier in round snapshots
        # so design plan-review rounds don't drop it; the raw archives below stay
        # excluded.
        *.failure-diag)
            return 0
            ;;
        *.dirty-tree|*.untracked-baseline|*.done|*.diag|*.sidecar|*.sidecar.history|*.events.jsonl|*.events.history)
            return 1
            ;;
        *-output.txt.prompt|*-output.txt.meta|*-output.txt.json|*-output.txt.cap-hit|*-vote-prompt.txt)
            return 1
            ;;
        findings.md|findings-in-scope.pre-dedup.md|findings-oos.md|findings-classification.tsv)
            return 0
            ;;
        oos.md|oos-accepted-design.md|oos-accepted-design.before.md|ballot.txt|voting-tally.md)
            return 0
            ;;
        round-meta.json|panel-manifest.ndjson)
            return 0
            ;;
        plan-review-slots.ndjson|plan-review-slots.pre-prune.ndjson|plan-voter-slots.ndjson|scout-plan-manifest.json|reviewer-prune-ledger.tsv|round-summary.env|round-start-s|plan.txt|plan-review-scope-anchor.txt)
            return 0
            ;;
        *-vote-output.txt|*-vote-output-first-pass.txt)
            return 0
            ;;
        voter*-diag.txt)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Return 0 when basename is included under plan-review/round-N/revise/; 1 when excluded.
design_round_revise_artifact_included() {
    local name="${1:-}"
    return 1
}

# Return 0 when basename is a known session-only artifact under round-N/revise/ that
# must not appear in committed design logs (silently skipped by design-log-publish.sh).
# Anything not matched by either function is an unexpected file and causes a hard error.
design_round_revise_artifact_excluded() {
    local name="${1:-}"
    case "$name" in
        # Raw vendor outputs and winning candidate patches
        *-output.txt|*-output-candidate.patch)
            return 0
            ;;
        # Revision outcome and prompt
        revise.env|prompt.txt)
            return 0
            ;;
        # Sidecars
        *.done|*.dirty-tree|*.meta|*.prompt|*.sidecar|*.sidecar.history|*.events.jsonl|*.events.history)
            return 0
            ;;
        *.untracked-baseline|*.diag|*.failure-diag|*.json)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}
