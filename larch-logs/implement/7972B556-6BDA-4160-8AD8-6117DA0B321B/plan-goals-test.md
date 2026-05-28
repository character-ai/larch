## Goal
Implement issue #3008: [IMPLEMENTING] [OOS] Gate B degraded-mode policy inconsistency and missing test coverage for --manual/-m\n\n## Out-of-Scope Observation.

## Implementation Plan
## Plan


This is a SIMPLE-tier design. Smallest change that closes the real gaps from #3008:
stale Gate B prose on the two runtime-authoritative surfaces can regress silently,
`write-run-params.sh` `--manual-gate-b` empty/missing rejection is not on the explicit
exit-2 path `assert_rejected_with` expects, and the SKILL.md Step 0b jq-merge recovery
has no automated harness. Sub-ask (1) "align surfaces" is closed as verified-aligned per
the Round 1 codebase scan and is intentionally out of scope.

## Files to modify/create

### UPDATED: `scripts/write-run-params.sh`

Replace the `${2:?--manual-gate-b requires a value}` expansion at line 95-97 with an
explicit missing/empty value check that emits `larch_err` and `exit 2` before
assignment:

```bash
        --manual-gate-b)
            if [[ $# -lt 2 || -z "${2-}" ]]; then
                larch_err "write-run-params.sh: --manual-gate-b requires a value"
                exit 2
            fi
            MANUAL_GATE_B="$2"
            shift 2
            ;;
```

Narrow scope: change only `--manual-gate-b`. Do **not** touch
`--partition-requested` (line 87-90) or `--brainstorm-requested` (line 91-94); those
keep their `${2:?...}` form because this PR does not also add matching empty/missing
tests for them. Do **not** cite `--review-budget` / `--workflow-path` as the model:
those use `if [[ $# -lt 2 ]]` only and accept empty strings (e.g.,
`--review-budget ""` is permitted upstream of the enum check), so their empty-value
behavior is intentionally different from this change.

Rationale: `${2:?...}` exits via the shell's null-parameter mechanism (typically rc=1
under `set -e`), not the script's `larch_err`+`exit 2` path, so `assert_rejected_with`
(which asserts rc==2 + stderr substring) cannot match empty/missing `--manual-gate-b`
until the parser is explicit. `[[ $# -lt 2 || -z "${2-}" ]]` covers both end-of-argv
missing and empty-string cases.

### UPDATED: `scripts/test-design-structure.sh`

Add a small block of `absent` checks that ban stale Gate B prose patterns. Insert the
block adjacent to the existing Gate B / `manual_gate_b` pin block (after the existing
`Gate B auto-apply / --manual pins` section). Use the existing `absent` helper:

```bash
absent "$APPROVAL_MD" 'no auto-apply' 'approval-gates.md: stale "no auto-apply" prose contradicts default auto-apply rule'
absent "$SKILL_MD"    'no auto-apply' 'SKILL.md: stale "no auto-apply" prose contradicts default auto-apply rule'
absent "$APPROVAL_MD" 'user is always prompted' 'approval-gates.md: stale "user is always prompted" prose contradicts default auto-apply rule'
absent "$SKILL_MD"    'user is always prompted' 'SKILL.md: stale "user is always prompted" prose contradicts default auto-apply rule'
absent "$APPROVAL_MD" 'Gate B always prompts' 'approval-gates.md: stale "Gate B always prompts" prose contradicts default auto-apply rule'
absent "$SKILL_MD"    'Gate B always prompts' 'SKILL.md: stale "Gate B always prompts" prose contradicts default auto-apply rule'
absent "$APPROVAL_MD" 'fail-closed to manual' 'approval-gates.md: stale "fail-closed to manual" prose contradicts degraded-mode auto-apply default'
absent "$SKILL_MD"    'fail-closed to manual' 'SKILL.md: stale "fail-closed to manual" prose contradicts degraded-mode auto-apply default'
```

Do **not** add a new degraded-mode `contains` pin for
`defaulting to auto-apply unless a true-only manual override is already present` — that
string is already pinned at line 556 in the existing Gate B block.

Add one new `grep -Fq` pin for the **full** Step 0b jq-merge filter (Check 19 already
pins the brainstorm arm at line 396 and Check 21 pins `manual_gate_b = $merge_m` at line
506; this single pin closes the remaining partition-arm gap and prevents partial drift).
Place a ShellCheck waiver on the line above so `make lint` does not flag the embedded
`$merge_*` in single quotes:

```bash
# shellcheck disable=SC2016 # jq filter literal: $merge_p/$merge_b/$merge_m are jq vars, not shell vars.
grep -Fq -- '.partition_requested = (.partition_requested == true or $merge_p) | .brainstorm_requested = (.brainstorm_requested == true or $merge_b) | .manual_gate_b = $merge_m' "$SKILL_MD" \
  || fail "(#3008) SKILL.md canonical Step 0b jq-merge filter must remain pinned for test-step0b-router-flag-recovery.sh"
```

Rationale: the `absent` set bans phrases that ONLY appear in stale Gate B contexts on
`$APPROVAL_MD` and `$SKILL_MD` only. `grep -Fq` matches fixed strings (per
`.claude/rules/`); no regex-injection risk. The full-filter pin proves all three merge
assignments stay present; do not claim a partition-only substring pin covers brainstorm
or manual semantics.

### UPDATED: `scripts/test-write-run-params.sh`

Add two failure-path test cases for `--manual-gate-b` **after** the writer parser
change above lands. Use the existing `assert_rejected_with` helper (line 21). Insert
near the existing `bad-manual-gate-b` enum test (lines 99-104):

```bash
assert_rejected_with manual-gate-b-empty 'write-run-params.sh: --manual-gate-b requires a value' \
    --classification SIMPLE \
    --manual-gate-b "" \
    --output "$TMPROOT/manual-gate-b-empty.json"

assert_rejected_with manual-gate-b-missing 'write-run-params.sh: --manual-gate-b requires a value' \
    --classification SIMPLE \
    --output "$TMPROOT/manual-gate-b-missing.json" \
    --manual-gate-b
```

Rationale: with explicit `larch_err` + `exit 2`, these cases match `assert_rejected_with`.
Existing tests only cover the enum-violation path (`maybe`). Do not add matching
empty/missing tests for `--partition-requested` / `--brainstorm-requested` — those flags
intentionally retain `${2:?...}` per the writer-parser scope narrowing above.

### NEW: `scripts/test-step0b-router-flag-recovery.sh`

New harness that exercises the SKILL.md Step 0b recovery path: the outer argv/jq guard
(both true-branch merge and false-branch no-op) and the jq-merge on an existing
`run-params.json`. Replicates the canonical shell from `skills/design/SKILL.md` Step
0b (merge expression + guard). CI pins the SKILL.md filter via the full jq pin above.

Structure:

```bash
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
```

Five cases: (1) success-path manual-only argv, (2) manual overwrite under reachable
guard, (3) partition OR-merge, (4) brainstorm OR-merge, (5) all-false no-op exercising
the guard's false branch.

### NEW: `scripts/test-step0b-router-flag-recovery.md`

Sibling per `.claude/rules/script-md-siblings.md`. Short stub:

```markdown
# test-step0b-router-flag-recovery.sh

**Purpose**: regression harness for the `SKILL.md` Step 0b router-flag recovery guard
and jq-merge. Exercises both true-branch merge (cases 1-4) and false-branch no-op
(case 5).

**Primary**: `scripts/write-run-params.sh` + `skills/design/SKILL.md` Step 0b.

**Edit-in-sync**: `merge_run_params()` and `recovery_merge_if_needed()` must match
`skills/design/SKILL.md` Step 0b. Drift is caught by the full jq-filter pin in
`scripts/test-design-structure.sh` (plus existing per-arm pins at lines 396 and 506).

**Run**: `bash scripts/test-step0b-router-flag-recovery.sh` or `make test-step0b-router-flag-recovery`.

**Coverage gap closed**: #3008 — `--manual-only` argv after successful
`write-run-params.sh` (case 1) and the outer guard's false-branch no-op (case 5).
```

### UPDATED: `Makefile`

Three small edits to register the new harness:

1. Add `test-step0b-router-flag-recovery` to the `.PHONY` line at line 4.
2. Add `test-step0b-router-flag-recovery` to `test-harnesses-6` (already hosts
   `test-write-run-params`) for cache locality.
3. Add the target near `test-write-run-params:`:

```make
test-step0b-router-flag-recovery:
	bash scripts/harness-timer.sh $@ bash scripts/test-step0b-router-flag-recovery.sh
```

## Approach

- Four concrete touch points: writer parser tightening on `--manual-gate-b` only,
  stale-prose lint, recovery harness, Makefile registration. No new shared libraries.
- Stale-prose lint scopes only `$APPROVAL_MD` and `$SKILL_MD` (runtime Gate B surfaces).
- Recovery harness copies both the outer guard and the inner jq merge from SKILL.md
  Step 0b, including a no-op false-branch case.
- Full jq-filter structural pin (plus existing per-arm pins) limits drift claims to
  what CI actually proves.
- `--manual-gate-b` rejection tests depend on the writer change landing first.
- SC2016 ShellCheck waivers go on both the harness jq literal and the new full-filter
  grep pin so `make lint` stays clean.

## Edge cases

- **Stale-prose false positive**: phrases are chosen for stale Gate B contract contexts
  on the two linted files only. Gate A "always prompts" prose is untouched because the
  lint targets composite phrases like `Gate B always prompts`.
- **Lint scope vs other docs**: `docs/configuration-and-permissions.md`, `SECURITY.md`,
  `docs/workflow-lifecycle.md`, and `AGENTS.md` are **not** scanned; stale Gate B phrases
  there regress silently unless caught manually — do not claim repo-wide CI protection.
- **Bash 3.2 portability**: harness uses `mktemp`, `trap`, plain `local`, `[[ ... ]]`,
  and `shasum -a 256` only (per `BASH_AUTHORING.md`).
- **Case 2 reachability**: recovery runs only when at least one argv router flag is
  true; case 2 uses `partition_requested=true` to enter the guarded path while
  asserting manual overwrite to `false`.
- **Case 5 no-op**: `shasum` before/after the recovery call proves the file is
  byte-identical when the guard short-circuits, so an always-merging guard regression
  fails this assertion.
- **Writer-parser narrowing**: `--partition-requested` and `--brainstorm-requested`
  retain their `${2:?...}` expansion. Their empty/missing-value behavior is unchanged
  by this PR.

## Failure modes

- **Stale-prose lint scope is narrow**: only `approval-gates.md` and
  `skills/design/SKILL.md` are checked. Stale phrases in other canonical docs
  (including `SECURITY.md` or `docs/configuration-and-permissions.md`) will **not**
  fail this harness — that is an intentional SIMPLE-tier scope limit, not a silent
  guarantee for those paths.
- **Recovery harness vs SKILL.md**: if SKILL.md changes the jq filter without updating
  this harness, case assertions may still pass locally until the full-filter pin in
  `test-design-structure.sh` fails. Warning signal: structural test failure on
  SKILL.md edit.
- **Makefile shard imbalance**: `test-harnesses-6` grows slightly; cosmetic only.
- **`--manual-gate-b` parser narrowing leaves sibling-flag drift**: if a future PR
  expects rc==2 on empty `--partition-requested` or `--brainstorm-requested`, that
  PR must update the parser at the same time. The lint cannot detect a future
  asymmetric expectation; it only guards the `--manual-gate-b` case introduced here.

## Testing strategy

Run before merge:

- `bash scripts/test-design-structure.sh` — new `absent` checks + full jq-filter pin.
- `bash scripts/test-write-run-params.sh` — new `manual-gate-b-empty` / missing cases
  (rc 2, stderr substring match).
- `bash scripts/test-step0b-router-flag-recovery.sh` — all five cases.
- `make lint` — shell-strict-mode, script-md-siblings, repo invariants.

No new fixtures or seed files beyond harness `mktemp` dirs.


## Acceptance

Landing this PR satisfies #3008 when:

1. `bash scripts/test-design-structure.sh` exits 0 with the new `absent` checks for stale Gate B phrases on `approval-gates.md` and `SKILL.md` and the new full-filter `grep -Fq` pin for the Step 0b jq-merge expression.
2. `bash scripts/test-write-run-params.sh` exits 0 with the two new `assert_rejected_with` cases for `--manual-gate-b` (empty value, missing value at end of argv), each asserting rc==2 and the stderr substring `write-run-params.sh: --manual-gate-b requires a value`.
3. `bash scripts/test-step0b-router-flag-recovery.sh` exits 0 with all five cases passing: (1) manual-only argv success path, (2) manual overwrite under reachable guard, (3) partition OR-merge, (4) brainstorm OR-merge, (5) all-false no-op exercising the guard's false branch.
4. `make test-step0b-router-flag-recovery` runs the new target.
5. `make lint` passes (shell-strict-mode, script-md-siblings present for the new `.sh`+`.md` pair, no ShellCheck SC2016 failures on the SC2016-waived jq literals).
6. `scripts/write-run-params.sh` retains `${2:?...}` for `--partition-requested` and `--brainstorm-requested` (writer-parser change is narrowed to `--manual-gate-b`).
7. The new test target is registered in the `Makefile` `.PHONY` line and a `test-harnesses-N` shard.

diff_lines: 330

## Test plan
(no test plan section in plan-file)
