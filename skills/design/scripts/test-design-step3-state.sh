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
printf 'prior accepted\n' >"$D4/accepted-plan-findings-all.md"
printf 'prior accepted snapshot\n' >"$D4/.accepted-plan-findings-all.prev.md"
printf 'prior oos\n' >"$D4/oos-accepted-design.md"
printf 'prior oos snapshot\n' >"$D4/.oos-accepted-design.prev.md"
printf '2\n' >"$D4/review-round-count.txt"
printf 'phase1\n' >"$D4/.step3-round-1.phase"
printf 'phase3\n' >"$D4/.step3-round-3.phase"
printf 'snapshot1\n' >"$D4/plan-pre-apply-round-1.txt"
printf 'snapshot3\n' >"$D4/plan-pre-apply-round-3.txt"
out=$(run_action "$D4" direct-review-entry)
[[ "$out" == *'STEP3_STATE=direct-review-entry'* ]] || fail "direct-review entry state missing: $out"
[[ ! -f "$D4/.step3-reentry" ]] || fail "direct-review entry did not consume marker"
[[ ! -e "$D4/.step3-round-1.phase" ]] || fail "direct-review entry left settled round-1 phase"
[[ -e "$D4/.step3-round-3.phase" ]] || fail "direct-review entry should preserve future round-3 phase"
[[ ! -e "$D4/plan-pre-apply-round-1.txt" ]] || fail "direct-review entry left settled round-1 apply snapshot"
[[ -e "$D4/plan-pre-apply-round-3.txt" ]] || fail "direct-review entry should preserve future round-3 apply snapshot"
[[ ! -f "$D4/accepted-plan-findings-all.md" ]] || fail "direct-review entry left stale cumulative accepted findings"
[[ ! -f "$D4/.accepted-plan-findings-all.prev.md" ]] || fail "direct-review entry left stale cumulative accepted snapshot"
[[ ! -f "$D4/oos-accepted-design.md" ]] || fail "direct-review entry left stale accepted OOS"
[[ ! -f "$D4/.oos-accepted-design.prev.md" ]] || fail "direct-review entry left stale accepted OOS snapshot"
[[ -f "$D4/.completed/step-1e" ]] || fail "direct-review entry missing step-1e"
for step in 2a 2b 2b.5; do
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
printf '2\n' >"$D6/review-round-count.txt"
printf 'phase1\n' >"$D6/.step3-round-1.phase"
printf 'phase3\n' >"$D6/.step3-round-3.phase"
printf 'snapshot1\n' >"$D6/plan-pre-apply-round-1.txt"
printf 'snapshot3\n' >"$D6/plan-pre-apply-round-3.txt"
printf 'prior cumulative\n' >"$D6/accepted-plan-findings-all.md"
printf 'prior cumulative snapshot\n' >"$D6/.accepted-plan-findings-all.prev.md"
printf 'prior oos\n' >"$D6/oos-accepted-design.md"
printf 'prior oos snapshot\n' >"$D6/.oos-accepted-design.prev.md"
out=$(run_action "$D6" auto-continuation-entry)
[[ "$out" == *'STEP3_STATE=auto-continuation-entry'* ]] || fail "auto continuation state missing: $out"
for step in 3 3.5 3b 4 4b; do
    [[ ! -f "$D6/.completed/step-$step" ]] || fail "auto continuation left stale step-$step"
done
[[ ! -e "$D6/.gate-b-postapply-ready-1" ]] || fail "auto continuation left stale Gate B marker"
[[ ! -e "$D6/.step3-round-1.phase" ]] || fail "auto continuation left settled round-1 phase"
[[ -e "$D6/.step3-round-3.phase" ]] || fail "auto continuation should preserve future round-3 phase"
[[ ! -e "$D6/plan-pre-apply-round-1.txt" ]] || fail "auto continuation left settled round-1 apply snapshot"
[[ -e "$D6/plan-pre-apply-round-3.txt" ]] || fail "auto continuation should preserve future round-3 apply snapshot"
grep -Fq 'prior cumulative' "$D6/accepted-plan-findings-all.md" || fail "auto continuation should preserve cumulative accepted findings"
grep -Fq 'prior cumulative snapshot' "$D6/.accepted-plan-findings-all.prev.md" || fail "auto continuation should preserve accepted findings snapshot"
grep -Fq 'prior oos' "$D6/oos-accepted-design.md" || fail "auto continuation should preserve accepted OOS"
grep -Fq 'prior oos snapshot' "$D6/.oos-accepted-design.prev.md" || fail "auto continuation should preserve accepted OOS snapshot"



echo "=== state helper ownership split stays narrow ==="
D7="$TMP/no-preview-clear"
mkdir -p "$D7/.completed"
: >"$D7/.step3-reentry"
: >"$D7/.step3-entry-plan-printed"
out=$(run_action "$D7" direct-review-entry)
[[ "$out" == *'STEP3_STATE=direct-review-entry'* ]] || fail "direct-review entry state missing: $out"
[[ -f "$D7/.step3-entry-plan-printed" ]] || fail "direct-review entry must not clear preview sentinel"

D8="$TMP/auto-no-preview-clear"
mkdir -p "$D8/.completed"
: >"$D8/.step3-entry-plan-printed"
out=$(run_action "$D8" auto-continuation-entry)
[[ "$out" == *'STEP3_STATE=auto-continuation-entry'* ]] || fail "auto-continuation state missing: $out"
[[ -f "$D8/.step3-entry-plan-printed" ]] || fail "auto-continuation state helper must not clear preview sentinel"

set +e
bad_out=$("$SUBJECT" --design-tmpdir "$D8" --postplan-operator-continue 2>&1)
bad_rc=$?
set -e
[[ "$bad_rc" -eq 2 ]] || fail "state helper should reject postplan operator mode rc=$bad_rc: $bad_out"
find "$TMP" -name '.postplan-operator-continue-*' -print -quit | grep -q . \
  && fail "state helper must not write postplan operator continue markers"
printf 'PASS: test-design-step3-state.sh\n'
