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
    design_round_artifact_included "$1" && fail "expected excluded: $1"
}

assert_revise_included() {
    design_round_revise_artifact_included "$1" || fail "expected revise included: $1"
}

assert_revise_excluded() {
    design_round_revise_artifact_included "$1" && fail "expected revise excluded: $1"
}

assert_included findings.md
assert_included findings-classification.tsv
assert_included accepted-plan-findings.md
assert_included round-summary.env
assert_included claude-vote-output.txt
assert_included voter1-diag.txt

assert_excluded cursor-plan-arch-output.txt
assert_excluded codex-plan-edge-output.txt
assert_excluded dyn-cursor-plan-foo-output.txt
assert_excluded cursor-plan-arch-output.txt.sidecar
assert_excluded cursor-plan-arch-output.txt.prompt
assert_excluded unknown.bin

assert_revise_included patch.diff
assert_revise_included revise.env
assert_revise_excluded extra-revise.log

printf '%s\n' 'test-lib-design-round-artifacts: ok'
