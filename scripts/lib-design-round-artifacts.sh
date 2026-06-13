# shellcheck shell=bash

# Default concise /design plan-review round allowlist. Full prose, per-reviewer
# transcripts, votes, manifests, and per-round plan/diff files are debug-only.
design_round_artifact_included() {
    case "${1:-}" in
        round-summary.env|findings-classification.tsv|prune-decision.env|prune-nit.env|reviewer-status.tsv)
            return 0
            ;;
        *-vote-output.txt|*-vote-output-first-pass.txt|*.failure-diag)
            [[ "${LARCH_FLUSH_DEBUG:-}" == "1" ]]
            return $?
            ;;
        *)
            return 1
            ;;
    esac
}

design_round_revise_artifact_included() {
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
        *.untracked-baseline|*.diag|*.failure-diag|*.json|*.stderr)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}
