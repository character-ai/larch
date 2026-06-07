#!/usr/bin/env bash
# Offline harness for design-step3-state.sh sentinel mutations.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/design-step3-state.sh"

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

[[ -x "$SUBJECT" ]] || fail "design-step3-state.sh must be executable"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-design-step3-state.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

run_action() {
    local dir="$1" action="$2"
    env LARCH_QUIET_DISABLE=1 "$SUBJECT" --design-tmpdir "$dir" "--$action"
}

echo "=== gate-b-bypass writes sentinels ==="
D1="$TMP/gate-b-bypass"
mkdir -p "$D1/.completed"
out=$(run_action "$D1" gate-b-bypass)
[[ "$out" == *'STEP3_STATE=gate-b-bypass'* ]] || fail "gate-b-bypass state missing: $out"
for step in 3 3.5; do
    [[ -f "$D1/.completed/step-$step" ]] || fail "gate-b-bypass missing step-$step"
done

echo "=== refused partial gate-b-bypass ==="
D2="$TMP/refused-partial"
mkdir -p "$D2/.completed"
: >"$D2/.completed/step-3.5"
set +e
out=$(run_action "$D2" gate-b-bypass)
rc=$?
set -e
[[ "$rc" -eq 1 ]] || fail "refused partial should exit 1, got $rc"
[[ "$out" == *'STEP3_STATE=refused-partial-gate-b-bypass'* ]] || fail "refused partial state missing: $out"

echo "=== direct-review-entry noop without marker ==="
D3="$TMP/direct-noop"
mkdir -p "$D3/.completed"
out=$(run_action "$D3" direct-review-entry)
[[ "$out" == *'STEP3_STATE=noop'* ]] || fail "direct-review noop missing: $out"

echo "=== direct-review-entry clears downstream and consumes marker ==="
D4="$TMP/direct-entry"
mkdir -p "$D4/.completed"
: >"$D4/.step3-reentry"
for step in 3 3.5 3b 4 4b; do
    : >"$D4/.completed/step-$step"
done
out=$(run_action "$D4" direct-review-entry)
[[ "$out" == *'STEP3_STATE=direct-review-entry'* ]] || fail "direct-review entry state missing: $out"
[[ ! -f "$D4/.step3-reentry" ]] || fail "direct-review entry did not consume marker"
[[ -f "$D4/.completed/step-1e" ]] || fail "direct-review entry missing step-1e"
for step in 2a 2a.5 2b 2b.5; do
    [[ -f "$D4/.completed/step-$step" ]] || fail "direct-review entry missing step-$step"
done
for step in 3 3.5 3b 4 4b; do
    [[ ! -f "$D4/.completed/step-$step" ]] || fail "direct-review entry left stale step-$step"
done

echo "=== direct-review-pause-hygiene keeps marker ==="
D5="$TMP/direct-pause-hygiene"
mkdir -p "$D5/.completed"
: >"$D5/.step3-reentry"
: >"$D5/.completed/step-3"
: >"$D5/.completed/step-3.5"
out=$(run_action "$D5" direct-review-pause-hygiene)
[[ "$out" == *'STEP3_STATE=direct-review-pause-hygiene'* ]] || fail "pause hygiene state missing: $out"
[[ -f "$D5/.step3-reentry" ]] || fail "pause hygiene consumed marker"
[[ ! -f "$D5/.completed/step-3" ]] || fail "pause hygiene left stale step-3"
[[ -f "$D5/.completed/step-2b.5" ]] || fail "pause hygiene missing bypass package"

echo "=== auto-continuation-entry clears unsafe Step 3 sentinels ==="
D6="$TMP/auto-continuation-entry"
mkdir -p "$D6/.completed"
for step in 3 3.5 3b 4 4b; do
    : >"$D6/.completed/step-$step"
done
: >"$D6/.gate-b-postapply-ready-1"
printf 'prior cumulative\n' >"$D6/accepted-plan-findings-all.md"
out=$(run_action "$D6" auto-continuation-entry)
[[ "$out" == *'STEP3_STATE=auto-continuation-entry'* ]] || fail "auto continuation state missing: $out"
for step in 3 3.5 3b 4 4b; do
    [[ ! -f "$D6/.completed/step-$step" ]] || fail "auto continuation left stale step-$step"
done
[[ ! -e "$D6/.gate-b-postapply-ready-1" ]] || fail "auto continuation left stale Gate B marker"
grep -Fq 'prior cumulative' "$D6/accepted-plan-findings-all.md" || fail "auto continuation should preserve cumulative accepted findings"

printf 'PASS: test-design-step3-state.sh\n'
