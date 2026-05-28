#!/usr/bin/env bash
# Shared per-round forensic artifact allowlist for plan-review-loop.sh and design-log-publish.sh.

# Return 0 when basename is included in plan-review/round-N/ staging; 1 when excluded.
design_round_artifact_included() {
    local name="$1"
    case "$name" in
        cursor-plan-*-output.txt|codex-plan-*-output.txt|dyn-*-output.txt)
            return 1
            ;;
        *.dirty-tree|*.untracked-baseline|*.done|*.diag|*.sidecar|*.events.jsonl)
            return 1
            ;;
        *-output.txt.prompt|*-output.txt.meta|*-output.txt.json|*-output.txt.cap-hit|*-vote-prompt.txt)
            return 1
            ;;
        findings.md|findings-in-scope.md|findings-oos.md|findings-classification.tsv)
            return 0
            ;;
        accepted-plan-findings.md|rejected-findings.md|oos.md|oos-accepted-design.md|ballot.txt|voting-tally.md)
            return 0
            ;;
        plan-review-slots.ndjson|plan-voter-slots.ndjson|scout-plan-manifest.json|round-summary.env|plan.txt)
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
    local name="$1"
    case "$name" in
        codex-output.txt|cursor-output.txt|claude-output.txt|codex-fallback-output.txt|cursor-fallback-output.txt|claude-fallback-output.txt|revise.env|prompt.txt|*-candidate.patch)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}
