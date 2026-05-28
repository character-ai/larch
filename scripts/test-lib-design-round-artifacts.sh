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

assert_included findings.md
assert_included findings-in-scope.md
assert_included findings-oos.md
assert_included findings-classification.tsv
assert_included accepted-plan-findings.md
assert_included rejected-findings.md
assert_included oos.md
# Canonical pin for issue #3143 group A (oos-accepted-design.md allowlist coverage).
assert_included oos-accepted-design.md
assert_included ballot.txt
assert_included voting-tally.md
assert_included plan-review-slots.ndjson
assert_included plan-voter-slots.ndjson
assert_included scout-plan-manifest.json
assert_included round-summary.env
assert_included plan.txt
assert_included claude-vote-output-first-pass.txt
assert_included claude-vote-output.txt
assert_included voter1-diag.txt

assert_excluded cursor-plan-arch-output.txt
assert_excluded codex-plan-edge-output.txt
assert_excluded dyn-cursor-plan-foo-output.txt
assert_excluded voter-output.txt.prompt
assert_excluded voter-output.txt.meta
assert_excluded voter-output.txt.json
assert_excluded voter-output.txt.cap-hit
assert_excluded ballot-vote-prompt.txt
assert_excluded vote-output.txt.events.jsonl
assert_excluded vote-output.txt.sidecar
assert_excluded vote-output.txt.done
assert_excluded vote-output.txt.diag
assert_excluded vote-output.txt.dirty-tree
assert_excluded vote-output.txt.untracked-baseline
assert_excluded cursor-plan-arch-output.txt.sidecar
assert_excluded cursor-plan-arch-output.txt.prompt
assert_excluded unknown.bin

assert_revise_included codex-output.txt
assert_revise_included cursor-output.txt
assert_revise_included claude-output.txt
assert_revise_included codex-fallback-output.txt
assert_revise_included cursor-fallback-output.txt
assert_revise_included claude-fallback-output.txt
assert_revise_included revise.env
assert_revise_included prompt.txt
assert_revise_included codex-candidate.patch
assert_revise_included codex-fallback-output-candidate.patch
assert_revise_included cursor-candidate.patch
assert_revise_included cursor-fallback-output-candidate.patch
assert_revise_included claude-candidate.patch
assert_revise_included claude-fallback-output-candidate.patch
assert_revise_excluded extra-revise.log

printf '%s\n' 'test-lib-design-round-artifacts: ok'
