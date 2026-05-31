## Goal
Implement issue #3274: [IMPLEMENTING] [OOS] cleanup.sh enumeration fail-open + predicate asymmetry docs, and remove stale LARCH_DESIGN_CONVERGENCE_THRESHOLD from approval-gates.md\n\n## Description.

## Implementation Plan
## Plan

Two independent workstreams plus a folded-in regression fix for issue #3274.

- **A. cleanup.sh enumeration fail-safe (#3260a)** — warn (not silent fail-open) when the top-level enumeration `find` fails, on both passes; sync docs/test/SECURITY.
- **B. Convergence-threshold dead-config removal (folded-in Step 3 regression)** — `run-step3-review.sh` forwards `--convergence-threshold` to `plan-review-loop.sh`, which rejects unknown options (exit 2). #3265 replaced per-round convergence with a hardcoded single-round rule (`CONVERGENCE_NON_NIT_MAX=5`) and removed the flag from the loop, so the env var is dead. Remove the plumbing end-to-end and add the missing integration-seam test.

**Already-resolved — NO edits (evidence-backed no-ops):**
- **#3255 (item 1)**: the stale `LARCH_DESIGN_CONVERGENCE_THRESHOLD` reference in `approval-gates.md` was already removed by #3265 — invariant #4 now cites `LARCH_DESIGN_ROUND_CAP` + "the hardcoded single-round convergence rule." Nothing to remove there. (Workstream B removes the env var that survives elsewhere; it does not re-touch `approval-gates.md`.)
- **#3260b (item 2.2)**: the cache vs `/tmp` `find` predicate asymmetry is already documented in `cleanup.md` ("The cache pass enumerates all non-symlink top-level entries with no age pre-filter … the `/tmp` pass pre-filters top-level entries by `-mtime +N`").

### UPDATED: `skills/cleanup/scripts/cleanup.sh`
Make the top-level enumeration `find` exit observable on both passes. Today both passes use `done < <(find … 2>/dev/null) || true`; process substitution hides `find`'s exit, so an enumeration failure (e.g. unreadable `~/.cache/larch/sessions/`) is silent.

- **Cache pass** (the `if [[ -d "$CACHE_DIR" ]]` block): allocate `$_cache_list` via guarded `mktemp`; on allocation failure, `larch_err "Warning: failed to allocate temp list for cache cleanup; skipping cache cleanup."` and skip (count 0). Else redirect enumeration into the temp file, branch on `find`'s exit, then read NUL-delimited from that file: `if find "$CACHE_DIR" -mindepth 1 -maxdepth 1 ! -type l -print0 >"$_cache_list" 2>/dev/null; then` … existing `while IFS= read -r -d $'\0' entry; do … done < "$_cache_list" || true` (loop body unchanged; retain `|| true`) … `else larch_err "Warning: failed to enumerate '$CACHE_DIR'; skipping cache cleanup."` … `fi`; `rm -f "$_cache_list"` on all paths.
- **`/tmp` pass** (the `if [[ -d "$TMP_ROOT" ]]` block): same wrap (guarded `mktemp` for `$_tmp_list` first), preserving the existing `-mtime +"$RETENTION_DAYS" \( "${_find_name_args[@]}" \)` predicate and the dir/file branch in the loop body. Allocation warning: `Warning: failed to allocate temp list for /tmp cleanup; skipping /tmp cleanup.` Enumeration warning: `Warning: failed to enumerate '$TMP_ROOT'; skipping /tmp cleanup.` Read loop: `done < "$_tmp_list" || true`.
- Temp files via `mktemp "${TMPDIR:-/tmp}/larch-cleanup-*.XXXXXX"`; `rm -f` after each pass on every path (success, `find` failure, allocation skip). Bash 3.2-only (no `mapfile`/assoc arrays).
- **Guard `mktemp` under `set -e`**: use `if _list=$(mktemp …); then` (or equivalent) so a missing/unwritable `${TMPDIR:-/tmp}` cannot abort cleanup before `emit_kv CACHE_REMOVED` / `TMP_REMOVED` — warn, skip that pass with count 0, continue.
- **Keep `|| true` on both `while read` loops** when reading from the temp file. The `if find` branch owns only top-level enumeration exit; removing `|| true` would let loop-body failures (e.g. `rm`) trip errexit and exit non-zero outside enumeration handling.
- **Invariant**: only top-level enumeration/allocation FAILURE paths change. Normal-path counts, NUL-safe iteration, `! -type l`, the `maxdepth 5` nested confirm, the `/tmp` `-mtime +N` pre-filter, loop-body errexit suppression (`|| true` on read loops), and the nested-scan fail-safe (`should_remove_by_age`, "failed to scan session activity") are preserved.

### UPDATED: `skills/cleanup/scripts/cleanup.md`
- Rewrite the "Enumeration-pass fail-open" invariant bullet: a failed top-level enumeration `find` or failure to allocate the temp list (`mktemp`) now emits a `larch_err` warning and skips that pass (counts stay 0; cleanup still exits 0 and still emits removal-count KVs) — a fail-safe parallel to the nested-scan fail-safe, no longer fail-open.
- Extend the **Edit-in-sync** bullet so it names the enumeration / temp-list allocation fail-safes (not only the nested-scan path) as triggers for updating `test-cleanup.sh` and `SECURITY.md`.

### UPDATED: `skills/cleanup/scripts/test-cleanup.sh`
- Add `write_stub_enum_failure`: a `find` stub that exits non-zero only when argv contains `-mindepth 1` (used solely by the two enumeration passes — the nested scan uses `-maxdepth 5`, the symlink reaper uses `-maxdepth 1` without `-mindepth`), else `exec /usr/bin/find "$@"`. Mirror the structure of the existing `write_stub_find_failure`.
- Add two cases mirroring the existing `find-failure-skips-deletion` / `-tmp` pair: `enumeration-failure-warns` (cache) and `enumeration-failure-warns-tmp` (/tmp). Each asserts: exit 0, output contains `failed to enumerate`, and `CACHE_REMOVED`/`TMP_REMOVED` == 0.
- Add `mktemp-allocation-failure-warns`: run with an unwritable `TMPDIR` (e.g. `export TMPDIR="$TMP/not-writable"`) so guarded `mktemp` fails before `find`; assert exit 0, the contract/stderr stream contains a temp-list allocation warning, affected pass count(s) == 0, and `CACHE_REMOVED`/`TMP_REMOVED` KVs are still present (cleanup did not abort under `set -e`).
- Leave the existing nested-scan failure cases intact (they still pass: enumeration `find` succeeds, only `-maxdepth 5` fails).

### UPDATED: `SECURITY.md`
In the `/cleanup` session-tmpdir retention note, change the clause "a failed top-level enumeration `find` is swallowed — the pass exits 0 with counts at 0 and emits no warning (fail-open)" to describe the new fail-safe: enumeration failure or failure to allocate the temp list for enumeration now warns via `larch_err` and skips that pass (count 0), cleanup still exits 0 and still emits removal-count KVs.

### UPDATED: `skills/design/scripts/run-step3-review.sh`
Remove the dead `--convergence-threshold` plumbing (the var is only forwarded — no other logic):
- Drop `--convergence-threshold N` from the usage string.
- Drop `CONVERGENCE_THRESHOLD=""` init, the `--convergence-threshold)` argv arm, and the `[[ -n "$CONVERGENCE_THRESHOLD" ]] || … required` check.
- Drop the `--convergence-threshold "$CONVERGENCE_THRESHOLD"` line from the `plan-review-loop.sh` invocation.
- Keep all `--round-cap` handling unchanged.

### UPDATED: `skills/design/scripts/run-step3-review.md`
Remove the `--convergence-threshold N` Argv table row and any "expands `${LARCH_DESIGN_CONVERGENCE_THRESHOLD:-3}`" note. Keep the `--round-cap` row.

### UPDATED: `skills/design/SKILL.md`
In the Step 3 `run-step3-review.sh` invocation, remove the `--convergence-threshold "${LARCH_DESIGN_CONVERGENCE_THRESHOLD:-3}"` argument line (keep `--round-cap "${LARCH_DESIGN_ROUND_CAP:-5}"`). No other Step 3 prose references the flag.

### UPDATED: `skills/design/references/flags.md`
- Fix the "Multi-round loop env vars" prose: `plan-review-loop.sh` validates `--round-cap` only (drop `--convergence-threshold`); the Step 3 driver passes only `${LARCH_DESIGN_ROUND_CAP:-5}`.
- Remove the `LARCH_DESIGN_CONVERGENCE_THRESHOLD` row from the env-var table (and its stale "two consecutive non-degraded rounds" semantics — superseded by the hardcoded single-round rule).

### UPDATED: `docs/configuration-and-permissions.md`
- Remove the `### LARCH_DESIGN_CONVERGENCE_THRESHOLD` section.
- Fix the following "Contrast with `LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD`" note so it refers to the singular remaining loop env var (`LARCH_DESIGN_ROUND_CAP`) instead of "the loop env vars above".

### UPDATED: `scripts/test-design-structure.sh`
Remove the two `contains` assertions that pin the dead forwarding: `run-step3-review.sh must pass convergence-threshold to plan-review-loop` and `SKILL must pass convergence-threshold to run-step3-review.sh`. Keep the two `--round-cap` pins.

### UPDATED: `skills/design/scripts/test-run-step3-review.sh`
- Remove `--convergence-threshold 3` from every passing-case invocation.
- Remove the `missing --convergence-threshold` exits-2 case and the `invalid convergence-threshold normalizes to panel-failed` case.
- Fix the `unknown option` case to use a still-valid bogus flag (drop the `--convergence-threshold 3` prefix, keep `--bogus`).
- **NEW integration-seam test** (the gap that hid this bug): add a case whose loop stub mirrors `plan-review-loop.sh`'s argv contract — accept only the real flags (`--design-tmpdir`, `--plan-file`, `--feature-file`, `--codex-present`, `--cursor-present`, `--round-num`, `--round-cap`, `--timeout`) and `exit 2` on any unknown option (the real loop's `*) … unknown option … exit 2` shape). Assert the driver drives it to a normal settled `LOOP_STATUS` (no `unknown option`, no `panel-failed` from a rejected forwarded flag). This catches future forwarding drift between the driver and the real loop.

### UPDATED: `skills/design/scripts/test-step3-review-cap.sh`
Remove `--convergence-threshold 3` from the `run_driver` helper invocation.

### UPDATED: `scripts/test-design-multi-round-integration.sh`
Remove `--convergence-threshold 3` from the `run-step3-review.sh` driver-boundary invocation.

**No change** to `skills/design/scripts/plan-review-loop.sh` (it correctly rejects unknown options; convergence is hardcoded via `CONVERGENCE_NON_NIT_MAX`) or `skills/design/scripts/test-plan-review-loop.sh` (its "removed `--convergence-threshold` flag rejected" case stays valid and now documents the intended end state).

### Approach
- Workstream A is localized failure-path instrumentation in one script + truthful doc/test/SECURITY sync. The temp-file wrap is the standard idiom for capturing `find`'s exit while keeping NUL-safe streaming; it is the minimal change that makes the failure observable without altering normal behavior.
- Workstream B is mechanical dead-config deletion. The env var has exactly one consumer chain (`SKILL.md` → `run-step3-review.sh` → forward), and the forward target rejects it. Removing it end-to-end fixes the live mismatch and completes the half-done removal the #3255 author assumed.
- The two workstreams are independent and could land as separate commits, but share one issue/PR.

### Edge cases
- **cleanup.sh**: `find` writes partial output then fails mid-enumeration → the `if find` branch catches the non-zero exit, the partial temp file is discarded (warn + skip), temp file removed. `mktemp` lives under `${TMPDIR:-/tmp}`, distinct from the scanned root, so the test's `LARCH_TEST_TMP_ROOT` override is unaffected.
- **`mktemp` failure**: missing/unwritable `${TMPDIR:-/tmp}` → guarded skip with `larch_err` warning, pass count 0, script continues to the next pass and still reaches `emit_kv` for both removal counts.
- **Existing nested-scan tests**: unaffected — the enumeration `find` succeeds; only the `-maxdepth 5` scan fails, so `should_remove_by_age` still warns "failed to scan session activity" and keeps the entry.
- **run-step3-review.sh callers**: only `SKILL.md` and the three test files pass `--convergence-threshold`; all are updated in the same change, so no caller is left passing a now-rejected flag to the driver.

### Failure modes
- **Unguarded `mktemp` (regression)**: without the guard, `set -e` aborts before `CACHE_REMOVED`/`TMP_REMOVED` KVs when the temp dir is bad — contradicts the planned fail-safe. Earliest signal: `mktemp-allocation-failure-warns`. Mitigation: guarded allocation on both passes.
- **Stub-key collision (test)**: keying `write_stub_enum_failure` on `-mindepth 1` is precise — the nested scan (`-maxdepth 5`) and symlink reaper (`-maxdepth 1`, no `-mindepth`) do not match, so the new test fails the enumeration only. Earliest signal: the existing nested-scan cases would break if the key were wrong. Mitigation: run the full `test-cleanup.sh` after editing.
- **Stale structure pin**: if the two `test-design-structure.sh` convergence pins are not removed, CI fails after dropping the forwarding. Earliest signal: `make lint` / structure harness. Mitigation: both assertions are in the file list.
- **Missed convergence reference**: a forgotten `--convergence-threshold` usage in a test leaves a now-invalid argv. Earliest signal: that test's run (driver no longer accepts the flag → exits 2). Mitigation: grep `convergence` across `skills/ scripts/ docs/` after edits; the complete surface is enumerated above.

### Testing strategy
- `bash skills/cleanup/scripts/test-cleanup.sh` — existing cases plus the two new enumeration-failure cases (cache + /tmp) and the mktemp-allocation-failure case.
- `bash skills/design/scripts/test-run-step3-review.sh` — updated convergence assertions + the new integration-seam case.
- `bash skills/design/scripts/test-step3-review-cap.sh`, `bash scripts/test-design-multi-round-integration.sh`, `bash skills/design/scripts/test-plan-review-loop.sh` — confirm green after argv edits.
- `bash scripts/test-design-structure.sh` — confirm green after removing the two convergence pins.
- `bash scripts/relevant-checks.sh` (or `make lint`) — repo-wide pre-commit incl. `make lint-bash32`, shellcheck, markdownlint, and `script-md-siblings`.

## Acceptance

- [ ] `cleanup.sh` emits a `larch_err` warning and skips the affected pass (count 0) when the top-level enumeration `find` fails on EITHER the cache pass or the `/tmp` pass; the script still exits 0 and still emits `SESSION_COUNT`/`CACHE_REMOVED`/`TMP_REMOVED`/`SYMLINKS_REMOVED` KVs.
- [ ] `cleanup.sh` emits a `larch_err` warning and skips the affected pass (count 0) when `mktemp` allocation fails (unwritable `${TMPDIR:-/tmp}`) — it does NOT abort under `set -e` before emitting count KVs.
- [ ] Normal-path cleanup behavior is byte-for-byte unchanged: NUL-safe iteration, `! -type l`, `maxdepth 5` nested confirm, `/tmp` `-mtime +N` pre-filter, `|| true` on read loops, and the existing nested-scan fail-safe.
- [ ] `cleanup.md` and `SECURITY.md` describe the enumeration path as a fail-safe (warn + skip), not fail-open; `cleanup.md` edit-in-sync note covers the new fail-safe.
- [ ] `test-cleanup.sh` adds `write_stub_enum_failure` plus the two enumeration-failure cases and the mktemp-allocation-failure case; the full suite passes; existing nested-scan cases still pass.
- [ ] `run-step3-review.sh` no longer accepts or forwards `--convergence-threshold`; the `SKILL.md` Step 3 call no longer passes it; `run-step3-review.md`, `flags.md`, and `docs/configuration-and-permissions.md` no longer document it.
- [ ] No `--convergence-threshold` / `CONVERGENCE_THRESHOLD` references remain across `skills/ scripts/ docs/` EXCEPT the intentional `test-plan-review-loop.sh` "removed flag rejected" case.
- [ ] `test-design-structure.sh` no longer pins the convergence forwarding; `test-run-step3-review.sh` adds the integration-seam test that exercises the real loop's reject-unknown contract; `test-step3-review-cap.sh` and `test-design-multi-round-integration.sh` no longer pass the flag.
- [ ] `/design` Step 3 plan review runs end-to-end against the real `plan-review-loop.sh` without the convergence shim.
- [ ] `make lint` (or `bash scripts/relevant-checks.sh`) and all named test harnesses pass.

diff_lines: 206

## Test plan
(no test plan section in plan-file)
