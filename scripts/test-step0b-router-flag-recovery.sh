#!/usr/bin/env bash
# Regression harness for design-init-runparams.sh Step 0b router-flag jq-merge recovery.
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

# Replicates design-init-runparams.sh Step 0b outer guard: recovery runs only when at least one argv flag
# is true and jq exists; when the output file is missing it warns and does not recreate it.
recovery_merge_if_needed() {
  local out="$1" partition_requested="$2" brainstorm_requested="$3" manual_requested="$4"
  if [[ "$partition_requested" == true || "$brainstorm_requested" == true || "$manual_requested" == true ]] && command -v jq >/dev/null 2>&1; then
    if [[ -f "$out" ]]; then
      merge_run_params "$out" "$partition_requested" "$brainstorm_requested" "$manual_requested"
    else
      printf '%s\n' "**⚠ 0b: run-params.json missing after write-run-params.sh; refusing to recreate it with fallback defaults. Re-run \`bash scripts/test-write-run-params.sh\` and fix the Step 0b contract drift first.**"
    fi
  fi
}

write_then_recover() {
  local out="$1" classification="$2" spy="$3" r_partition="$4" r_brainstorm="$5" r_manual="$6"
  if ! "$WRITER" --classification "$classification" \
      --partition-requested false --brainstorm-requested false --manual-gate-b false \
      --output "$out" >/dev/null 2>&1; then
    return 1
  fi
  recovery_merge_if_needed "$out" "$r_partition" "$r_brainstorm" "$r_manual" || return 1
  : > "$spy"
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

# Case 6: missing run-params.json under a true argv flag warns and does not recreate fallback defaults.
OUT6="$TMPROOT/case6.json"
warning_case6=$(recovery_merge_if_needed "$OUT6" true false false)
[[ ! -e "$OUT6" ]] || fail "case6: missing-file degraded path recreated $OUT6"
[[ "$warning_case6" == "**⚠ 0b: run-params.json missing after write-run-params.sh; refusing to recreate it with fallback defaults. Re-run \`bash scripts/test-write-run-params.sh\` and fix the Step 0b contract drift first.**" ]] \
  || fail "case6: missing-file degraded warning drifted; got: $warning_case6"

# Case 7: a failing writer aborts BEFORE recovery (#3161). Spy absence proves recovery never
# ran; captured stdout proves the missing-file recovery warning was not emitted.
OUT7="$TMPROOT/case7.json"; SPY7="$TMPROOT/case7-recovery-reached"; rm -f "$SPY7"
set +e
out7_stdout=$(write_then_recover "$OUT7" BOGUS "$SPY7" false false true 2>/dev/null)
rc7=$?
set -e
[[ "$rc7" -ne 0 ]] || fail "case7: failing writer must abort before recovery; rc=$rc7"
[[ ! -e "$SPY7" ]] || fail "case7: recovery completed after writer failure (spy present)"
[[ ! -e "$OUT7" ]] || fail "case7: failing writer created $OUT7"
[[ "$out7_stdout" != *"refusing to recreate it with fallback defaults"* ]] \
  || fail "case7: missing-file recovery warning emitted after writer failure (recovery not bypassed)"

# Case 7b (positive control): a successful write reaches AND completes recovery. Writer writes
# manual_gate_b=false; recovery (manual=true) must FLIP it to true. Spy present only because
# recovery returned 0.
OUT7B="$TMPROOT/case7b.json"; SPY7B="$TMPROOT/case7b-recovery-reached"; rm -f "$SPY7B"
set +e; write_then_recover "$OUT7B" SIMPLE "$SPY7B" false false true; rc7b=$?; set -e
[[ "$rc7b" -eq 0 ]] || fail "case7b: successful write_then_recover returned $rc7b"
[[ -e "$SPY7B" ]] || fail "case7b: recovery did not complete after successful write (spy absent)"
jq -e '.manual_gate_b == true' "$OUT7B" >/dev/null \
  || fail "case7b: recovery did not flip manual_gate_b false->true; got $(cat "$OUT7B")"

echo "PASS: test-step0b-router-flag-recovery.sh"
