#!/usr/bin/env bash
# Offline harness for scripts/lib-design-round-artifacts.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
# shellcheck source=scripts/lib-design-round-artifacts.sh
source "$ROOT/scripts/lib-design-round-artifacts.sh"

fail() { printf '%s\n' "$1" >&2; exit 1; }

assert_included() {
    design_round_artifact_included "$1" || fail "expected included: $1"
}

assert_excluded() {
    if design_round_artifact_included "$1"; then
        fail "expected excluded: $1"
    fi
}

assert_revise_included() {
    design_round_revise_artifact_included "$1" || fail "expected revise included: $1"
}

assert_revise_excluded() {
    if design_round_revise_artifact_included "$1"; then
        fail "expected revise excluded: $1"
    fi
}

assert_included round-summary.env
assert_included findings-classification.tsv
assert_included prune-decision.env
assert_included prune-nit.env

assert_excluded findings.md
assert_excluded findings-in-scope.md
assert_excluded findings-oos.md
assert_excluded accepted-plan-findings.md
assert_excluded rejected-findings.md
assert_excluded oos.md
assert_excluded oos-accepted-design.md
assert_excluded oos-accepted-design.before.md
assert_excluded ballot.txt
assert_excluded voting-tally.md
assert_excluded plan-review-slots.ndjson
assert_excluded plan-voter-slots.ndjson
assert_excluded scout-plan-manifest.json
assert_excluded reviewer-prune-ledger.tsv
assert_excluded round-start-s
assert_excluded plan.txt
assert_excluded plan.diff
assert_excluded claude-vote-output-first-pass.txt
assert_excluded claude-vote-output.txt
assert_excluded voter1-diag.txt
assert_excluded panel-manifest.ndjson
assert_excluded round-meta.json

assert_revise_excluded codex-output.txt
assert_revise_excluded cursor-output.txt
assert_revise_excluded claude-output.txt
assert_revise_excluded revise.env
assert_revise_excluded prompt.txt
assert_revise_excluded codex-output-candidate.patch
assert_revise_excluded cursor-output-candidate.patch
assert_revise_excluded claude-output-candidate.patch
assert_revise_excluded extra-revise.log

# Explicit exclusion list: known session-only artifacts silently skipped at publish time.
assert_revise_explicitly_excluded() {
    design_round_revise_artifact_excluded "$1" || fail "expected revise explicitly excluded: $1"
}
assert_revise_not_explicitly_excluded() {
    if design_round_revise_artifact_excluded "$1"; then
        fail "expected revise NOT explicitly excluded (unknown file): $1"
    fi
}
assert_revise_explicitly_excluded codex-output.txt
assert_revise_explicitly_excluded cursor-output.txt
assert_revise_explicitly_excluded codex-output-candidate.patch
assert_revise_explicitly_excluded cursor-output-candidate.patch
assert_revise_explicitly_excluded claude-output-candidate.patch
assert_revise_explicitly_excluded revise.env
assert_revise_explicitly_excluded prompt.txt
assert_revise_explicitly_excluded codex-output.txt.done
assert_revise_explicitly_excluded codex-output.txt.dirty-tree
assert_revise_explicitly_excluded codex-output.txt.prompt
assert_revise_explicitly_excluded codex-output.txt.meta
assert_revise_explicitly_excluded codex-output.txt.sidecar
assert_revise_explicitly_excluded codex-output.txt.events.jsonl
assert_revise_explicitly_excluded codex-output.txt.untracked-baseline
assert_revise_explicitly_excluded codex-output.txt.diag
assert_revise_explicitly_excluded codex-output.txt.failure-diag
assert_revise_explicitly_excluded codex-output.txt.json
assert_revise_explicitly_excluded claude-output.txt.stderr
assert_revise_not_explicitly_excluded extra-revise.log

printf '%s\n' 'test-lib-design-round-artifacts: ok'
