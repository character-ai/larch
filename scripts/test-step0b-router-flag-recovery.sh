#!/usr/bin/env bash
# Regression harness for SKILL.md Step 0b router-flag jq-merge recovery.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
WRITER="$REPO_ROOT/scripts/write-run-params.sh"

fail() { echo "FAIL: $1" >&2; exit 1; }
TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-step0b-recovery.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

merge_run_params() {
  local out="$1" partition_requested="$2" brainstorm_requested="$3" manual_requested="$4"
  local _rp_merge _rp_err
  _rp_merge=$(mktemp "${TMPDIR:-/tmp}/larch-router-flags-merge.XXXXXX")
  _rp_err=$(mktemp "${TMPDIR:-/tmp}/larch-router-flags-merge-err.XXXXXX")
  # shellcheck disable=SC2016 # jq filter literal: $merge_p/$merge_b/$merge_m are jq vars, not shell vars.
  jq -c \
    --argjson merge_p "$([[ "$partition_requested" == true ]] && echo true || echo false)" \
    --argjson merge_b "$([[ "$brainstorm_requested" == true ]] && echo true || echo false)" \
    --argjson merge_m "$([[ "$manual_requested" == true ]] && echo true || echo false)" \
    '.partition_requested = (.partition_requested == true or $merge_p) | .brainstorm_requested = (.brainstorm_requested == true or $merge_b) | .manual_gate_b = $merge_m' \
    "$out" >"$_rp_merge" 2>"$_rp_err" || { cat "$_rp_err" >&2; rm -f "$_rp_merge" "$_rp_err"; return 1; }
  mv -f "$_rp_merge" "$out"
  rm -f "$_rp_err"
}

# Replicates SKILL.md Step 0b outer guard: recovery runs only when at least one argv flag
# is true and jq exists, and only merges when the output file already exists.
recovery_merge_if_needed() {
  local out="$1" partition_requested="$2" brainstorm_requested="$3" manual_requested="$4"
  if [[ "$partition_requested" == true || "$brainstorm_requested" == true || "$manual_requested" == true ]] && command -v jq >/dev/null 2>&1; then
    [[ -f "$out" ]] || fail "recovery_merge_if_needed: missing $out"
    merge_run_params "$out" "$partition_requested" "$brainstorm_requested" "$manual_requested"
  fi
}

# Case 1: successful write; manual-only argv => manual=true (FINDING_9 success path).
OUT1="$TMPROOT/case1.json"
"$WRITER" --classification SIMPLE --partition-requested false --brainstorm-requested false --manual-gate-b false --output "$OUT1" >/dev/null
recovery_merge_if_needed "$OUT1" false false true
jq -e '.partition_requested == false and .brainstorm_requested == false and .manual_gate_b == true' "$OUT1" >/dev/null \
  || fail "case1: manual-only argv merge produced $(cat "$OUT1")"

# Case 2: stored manual=true; argv partition=true + manual=false => manual=false when recovery runs.
# Reachable runtime shape: outer guard true because partition_requested=true; manual overwrite
# clears stale persisted manual (SKILL.md Step 0b rationale).
OUT2="$TMPROOT/case2.json"
"$WRITER" --classification SIMPLE --partition-requested false --brainstorm-requested false --manual-gate-b true --output "$OUT2" >/dev/null
recovery_merge_if_needed "$OUT2" true false false
jq -e '.manual_gate_b == false and .partition_requested == true' "$OUT2" >/dev/null \
  || fail "case2: manual overwrite under reachable guard failed; got $(cat "$OUT2")"

# Case 3: stored partition=true; argv partition=false, brainstorm=true => OR-merge preserves partition.
OUT3="$TMPROOT/case3.json"
"$WRITER" --classification SIMPLE --partition-requested true --brainstorm-requested false --manual-gate-b false --output "$OUT3" >/dev/null
recovery_merge_if_needed "$OUT3" false true false
jq -e '.partition_requested == true and .brainstorm_requested == true and .manual_gate_b == false' "$OUT3" >/dev/null \
  || fail "case3: partition OR-merge regressed; got $(cat "$OUT3")"

# Case 4: stored brainstorm=true; guard enters via partition argv true; brainstorm OR-merge preserves.
OUT4="$TMPROOT/case4.json"
"$WRITER" --classification SIMPLE --partition-requested false --brainstorm-requested true --manual-gate-b false --output "$OUT4" >/dev/null
recovery_merge_if_needed "$OUT4" true false false
jq -e '.brainstorm_requested == true and .partition_requested == true and .manual_gate_b == false' "$OUT4" >/dev/null \
  || fail "case4: brainstorm OR-merge regressed; got $(cat "$OUT4")"

# Case 5: all-false argv => outer guard short-circuits; file unchanged (false-branch no-op).
# Proves the guard's false-branch is exercised so a loosened guard would fail this assertion.
OUT5="$TMPROOT/case5.json"
"$WRITER" --classification SIMPLE --partition-requested false --brainstorm-requested false --manual-gate-b false --output "$OUT5" >/dev/null
before_sum=$(shasum -a 256 "$OUT5" | awk '{print $1}')
recovery_merge_if_needed "$OUT5" false false false
after_sum=$(shasum -a 256 "$OUT5" | awk '{print $1}')
[[ "$before_sum" == "$after_sum" ]] || fail "case5: all-false guard mutated file; before=$before_sum after=$after_sum"
jq -e '.partition_requested == false and .brainstorm_requested == false and .manual_gate_b == false' "$OUT5" >/dev/null \
  || fail "case5: all-false post-state mismatch"

echo "PASS: test-step0b-router-flag-recovery.sh"
