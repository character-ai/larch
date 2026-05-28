## Goal
Implement issue #3161: [IMPLEMENTING] Write-failure recovery in test-step0b-router-flag-recovery.sh remains unproven\n\n## Out-of-Scope Observation.

## Implementation Plan
## Plan

Close OOS #3161 by proving, in the existing regression harness, that the Step 0b
router-flag recovery merge is bypassed on a hard `write-run-params.sh` failure.
SIMPLE-tier minimum change: edit two files only. No `/design` behavior change.

### Context (hard constraint)

SKILL.md Step 0b treats a non-zero `write-run-params.sh` exit as contract drift and
`exit 1`s **before** the router-flag recovery block. So recovery is unreachable on a
hard writer failure. `scripts/test-design-structure.sh` forbids any "run-params write
failed; router-flag recovery" prose in SKILL.md. The new case must encode this
boundary, not contradict it. The current harness only models the recovery guard
(`recovery_merge_if_needed`) over successful writes (cases 1-5) and the missing-file
degraded warning (case 6); it never models the writer-invocation + abort decision.

### Review findings incorporated

Plan review accepted two findings; both are folded into the design below:
- FINDING_1 (Codex-Arch): the spy must mark recovery *completion*, and Case 7 must
  assert the missing-file recovery warning is absent.
- FINDING_2 (Cursor/Codex-Requirements): the 7b assertion must check a value recovery
  *changes*, not one the writer already wrote.

## Files to modify/create

### UPDATED: `scripts/test-step0b-router-flag-recovery.sh`

Add a harness-local helper and one new case (with a positive control). Do not touch
cases 1-6 or the `merge_run_params()` / `recovery_merge_if_needed()` helpers.

- Add `write_then_recover()` after `recovery_merge_if_needed()`. It models SKILL.md
  Step 0b sub-step 6: run `write-run-params.sh` (writing an all-false baseline); on
  non-zero exit `return 1` WITHOUT calling `recovery_merge_if_needed` (the SKILL.md
  `exit 1` abort); on success, call `recovery_merge_if_needed` with the supplied
  recovery flags, then touch the spy ONLY after recovery returns 0. The spy therefore
  marks recovery completion, not merely "past the writer".
- Add Case 7: inject a writer failure with invalid argv (`--classification BOGUS`).
  Assert the helper returns non-zero, the spy is absent (recovery never completed), no
  `run-params.json` was created, and captured stdout does NOT contain the missing-file
  recovery warning (so recovery was never attempted on the missing file).
- Add Case 7b (positive control): a successful SIMPLE write. The writer writes
  `manual_gate_b=false`; recovery is called with `manual=true` and must FLIP it to
  true. Assert the helper returns 0, the spy is present (recovery completed), and
  `manual_gate_b == true` — a value recovery changed, not one the writer wrote.

```bash
# Add after recovery_merge_if_needed():
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
```

### UPDATED: `scripts/test-step0b-router-flag-recovery.md`

- Update Purpose and the case enumeration to include the writer-failure abort case (7)
  and its success-path positive control (7b).
- Add a `**Coverage gap closed**` line for #3161 (writer-failure abort precedes recovery).
- Note `write_then_recover()` composes (does not modify) `recovery_merge_if_needed()`, so
  the existing edit-in-sync jq-filter pins remain unaffected.

## Approach

The OOS framing ("writer failure + recovery") is ambiguous because SKILL.md aborts before
recovery. Resolve it by encoding the actual boundary in an executable case: a failing writer
must short-circuit recovery. Inject the failure with the real `write-run-params.sh` (invalid
`--classification`) rather than a mock. Tie the spy to recovery *completion*, and make Case 7b
assert a value recovery changes (writer writes `manual=false`; recovery flips it to `true`).

## Edge cases

- Invalid `--classification BOGUS` makes `write-run-params.sh` `exit 2` during enum
  validation, before any output file is created — so the no-file assertion holds.
- If a regression wrongly invoked recovery after the writer failure, `recovery_merge_if_needed`
  would hit its missing-file branch (returns 0, prints the warning) — so the spy WOULD be
  touched and the warning WOULD appear. Case 7's spy-absent and warning-absent assertions both
  catch that regression.
- `set +e` / `set -e` wraps the helper calls so the harness's `set -euo pipefail` does not
  abort on the intentional non-zero return in Case 7.

## Failure modes

- False pass (helper always returns 1) → Case 7 passes trivially. Mitigated by the 7b
  positive control asserting the success path reaches AND completes recovery.
- Writer behavior drift (invalid argv stops failing, or starts creating partial output)
  → Case 7 fails loudly on the rc / no-file / warning assertions.
- Spy-file staleness across cases → each case uses a unique spy path and `rm -f`s it
  before the call.

## Testing strategy

- Run `bash scripts/test-step0b-router-flag-recovery.sh` (and `make test-step0b-router-flag-recovery`); expect `PASS:` with cases 1-7b green.
- Run `bash scripts/test-design-structure.sh` to confirm the SKILL.md Step 0b pins are unchanged.
- Run `bash scripts/relevant-checks.sh` for the touched files.

## Acceptance

Landing this PR closes #3161 when:

1. `bash scripts/test-step0b-router-flag-recovery.sh` exits 0 with new cases 7 and 7b passing alongside the existing cases 1-6 (terminal `PASS:` line).
2. Case 7 asserts a failing writer (invalid `--classification`) aborts before recovery: non-zero return, spy absent, no `run-params.json` created, and the missing-file recovery warning absent from captured stdout.
3. Case 7b (positive control) asserts a successful write reaches and completes recovery: the helper returns 0, the spy is present, and recovery flips `manual_gate_b` from the writer's `false` baseline to `true`.
4. The new `write_then_recover()` helper composes (does not modify) `merge_run_params()` / `recovery_merge_if_needed()`; cases 1-6 are unchanged.
5. `bash scripts/test-design-structure.sh` exits 0 — the Step 0b jq-filter, guard, and absent-prose pins are unchanged (no SKILL.md behavior change, no new pin).
6. `scripts/test-step0b-router-flag-recovery.md` documents cases 7/7b and adds a `**Coverage gap closed**` line for #3161.
7. `make test-step0b-router-flag-recovery` and `make lint` pass (shell-strict-mode, script-md-siblings).

diff_lines: 46

## Test plan
(no test plan section in plan-file)
