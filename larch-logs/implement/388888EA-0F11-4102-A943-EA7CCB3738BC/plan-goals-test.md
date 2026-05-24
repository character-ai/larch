## Goal
Add launcher failure classification KVs and short-circuit CI-fix waterfall on non-health first-fixer failure

## Implementation Plan
## Plan

### Canonical KV tokens (single source of truth)

The classification grammar is pinned by name and enforced by structural tests so future renames trigger CI failures rather than silent drift.

- `LAUNCHER_FAILURE_CLASS` enum: exactly one of `none` / `health` / `other`.
- `LAUNCHER_FAILURE_REASON` enum: exactly one of `auth` / `binary-missing` / `health-probe` / `timeout` / `parse` / `refusal` / `unknown` (empty on `LAUNCHER_FAILURE_CLASS=none`).

The literal `parse` is used everywhere. The reason for auth failure after the in-launcher retry exhausts is `auth` (the existing `append_launch_failure` diagnostic string `auth-retries-exhausted` is a separate sidecar value, not one of the canonical reason tokens). `binary-missing` is the canonical reason when the launcher cannot resolve the underlying CLI binary.

`no-action` / `refusal` outcomes that occur on `LAUNCHER_EXIT=0` are EXPLICITLY OUT OF SCOPE for this issue — they require post-exit-0 detection (empty-diff baseline comparison or output pattern matching) that the launchers do not perform today. A follow-up issue will extend the reason enum with those tokens. This issue covers launcher-detectable failures only (timeout, parse, generic non-zero CLI exit, refusal-by-CLI-exit-code).

### Files to modify/create

- `scripts/lib-external-launcher-common.sh` — add `external_classify_launch_failure` helper consuming `LAUNCHER_EXIT`, sidecar log path, and the existing `external_auth_verdict` output; print canonical KVs to stdout. Health = `binary-missing` / `auth` (after retry exhausts) / `health-probe`. Every other launcher-detectable failure = `other`. `LAUNCHER_EXIT=0` ⇒ `none`. Binary-presence is signaled by the launcher's existing `command -v <binary>` precondition via an explicit caller argument so the early-exit path can still emit KVs.

- `scripts/launch-cursor-ci.sh` — in the existing `emit_kv LAUNCHER_EXIT` block, call the new helper and emit both KVs unconditionally. On `command -v cursor` failure (or any early `die()` representing "tool unavailable to start"), emit `LAUNCHER_FAILURE_CLASS=health LAUNCHER_FAILURE_REASON=binary-missing` BEFORE the die. The pre-spawn argv-validation `die()` (exit 2) is NOT in scope — argv mismatches are caller bugs, not first-fixer failures.

- `scripts/launch-codex-ci.sh` — parity change to cursor.

- `scripts/launch-claude-ci.sh` — parity change. Claude tier is not the policy's first fixer, but the contract is uniform so `run_ci_fix_vendor` consumes the same KV regardless of tier.

- `scripts/ship-pr.sh` —
  - `needs_user_bail_reason()` allowlist: add `first-fixer-non-health` alongside existing tokens.
  - `run_ci_fix_vendor()` for-tier loop: after `record_failure` + `_ci_fix_rollback` in the general failure branch, add a guard firing only when `tier == cursor` AND `LAUNCHER_FAILURE_CLASS=other` parsed from `$fail_file`. On match: `state_set_many BAIL_REASON=first-fixer-non-health BAIL_FAILURE_DETAIL_LOG=$fail_file`, emit a breadcrumb, and RETURN NON-ZERO from `run_ci_fix_vendor` (NOT `exit 3` direct). Outer `run_evaluate_failure` / `run_ci_phase` then takes its existing `bail)` branch through the standard exit-3 sequence. On `LAUNCHER_FAILURE_CLASS=health` (or `none` / missing — defaults to `health` per Edge case #2), keep existing fall-through to the next tier. For `tier != cursor`, never short-circuit. **`wrapper_rc == 2` is EXCLUDED**: that path is launcher `die()` argv validation that exits before emitting any KV; existing rollback + continue-to-next-tier is preserved.
  - `BAIL_NEEDS_USER_INPUT` is NOT set on this new bail path. It is set only on the existing user-bail fall-through inside `/implement` after sentinel/counter exhaustion.

- `skills/implement/SKILL.md` — single bullet covering both the new Step 8+ Exit 3 procedure AND the documentation note. Extend the Step 8+ Exit 3 branch to special-case `BAIL_REASON=first-fixer-non-health`. New control flow runs BEFORE the existing `AskUserQuestion` path:
  1. Read `FAILED_RUN_ID` from `ship-pr-state.sh` (set by `run_evaluate_failure` via `state_set FAILED_RUN_ID`, non-empty invariant asserted at run_evaluate_failure entry). Read `REPO` similarly.
  2. Check `read_state FORKED_TARGET` and `read_state REPO_UNAVAILABLE`. If either is `true`, skip the autonomous path; fall through to the existing user-bail flow.
  3. Sentinel path: `$IMPLEMENT_TMPDIR/main-agent-ci-fix-$FAILED_RUN_ID.attempted`. Counter path: `$IMPLEMENT_TMPDIR/main-agent-ci-fix.count` (initialized to `0` if missing on read). Cap of `3` is inclusive of the maximum attempts: policy fires on read values 0/1/2 (attempts 1/2/3); read value `3` falls through. If sentinel exists OR counter `>= 3`, fall through.
  4. Write sentinel and increment counter BEFORE any repo edits. Fail-closed: any write failure aborts the autonomous path; log `Tool Failures` to `execution-issues.md`.
  5. Capture fresh CI failure log: `gh-run-logs.sh --run-id "$FAILED_RUN_ID" --repo "$REPO" | redact-secrets.sh > $IMPLEMENT_TMPDIR/main-agent-ci-fix-$FAILED_RUN_ID.gh-run-logs.redacted.txt`. ALSO redact `BAIL_FAILURE_DETAIL_LOG` through `redact-secrets.sh` before reading; validate the path is under `$IMPLEMENT_TMPDIR` to prevent traversal.
  6. Use Claude tool calls to make the minimal repo edit, informed by the redacted CI log (primary) and redacted launcher diagnostic (supplemental).
  7. Run `run-relevant-checks-captured.sh` (or `scripts/relevant-checks.sh`). On failure, log to `execution-issues.md` and fall through to user-bail.
  8. Stage edited files explicitly via `git add -- <paths>` (mirrors `ship-pr.sh` CI-fix path; do NOT use `git add -A`).
  9. Commit via `git-commit.sh -m "Fix CI failure (main-agent)"`.
  10. Refresh run-log token/timing artifacts: `refresh-run-logs.sh --state-file --implement-tmpdir` (mirrors existing CI-fix push sequence).
  11. Push via `git-push.sh`.
  12. Re-invoke `ship-pr.sh` foreground with the same `Invoke:` argv (no `--resume-phase`).

  Doc note at the top of the Step 8+ Exit 3 prose enumerates `first-fixer-non-health` token + sentinel/cap policy.

- `scripts/test-ship-pr.sh` — cases:
  - cursor returns `LAUNCHER_FAILURE_CLASS=health LAUNCHER_FAILURE_REASON=binary-missing` ⇒ fall-through to codex/claude; existing all-vendors-failed behavior preserved.
  - cursor returns `LAUNCHER_FAILURE_CLASS=other LAUNCHER_FAILURE_REASON=timeout` ⇒ only cursor invoked; codex/claude NOT invoked; `run_ci_fix_vendor` returns non-zero; outer flow exits 3; state `BAIL_REASON=first-fixer-non-health`; `BAIL_FAILURE_DETAIL_LOG` set; `BAIL_NEEDS_USER_INPUT=false`.
  - cursor succeeds ⇒ no waterfall, no policy.
  - codex (tier 2) non-health failure ⇒ existing waterfall to claude; policy does NOT fire for non-first tiers.
  - Run-loop symmetry: policy fires on every `run_ci_fix_vendor` entry (FIX_ATTEMPTS=0/1/2).
  - `wrapper_rc=2` at cursor ⇒ existing rollback + continue (policy does NOT fire — launcher never emitted KVs).
  - Canonical-token pinning: each literal token appears verbatim in helper + 3 launchers + ship-pr.sh guard.

- `scripts/test-launch-review.sh` (and any direct `test-launch-*-ci.sh`) — assert new KVs emitted with correct values across health vs other scenarios. Focused harness `test-lib-external-launcher-common.sh`: binary-missing→health; auth-retries-exhausted→health/auth; health-probe failure→health/health-probe; timeout→other/timeout; parse→other/parse; generic non-zero→other/unknown; LAUNCHER_EXIT=0→none/empty.

- `scripts/test-implement-structure.sh` — (a) assert new Step 8+ sub-steps 1-12 present and ordered; (b) drop/invert the existing prior-state rule at the line range that forbade "main-agent CI repair" prose.

- New mock harness (or extension of existing) covering `/implement` Step 8+ loop: sentinel-exists short-circuit, counter cap exhaustion (3 attempts → 4th falls through), sentinel write failure, missing `FAILED_RUN_ID`, `FORKED_TARGET=true` / `REPO_UNAVAILABLE=true` gates.

- Sibling `.md`s (per `script-md-siblings.md`): `lib-external-launcher-common.md` (classifier helper contract, canonical KV grammar, binary-presence mechanism), `launch-{cursor,codex,claude}-ci.md` (new KV emit-block + emit-before-die), `ship-pr.md` (new BAIL_REASON token, new state key `BAIL_FAILURE_DETAIL_LOG`, explicit note that `BAIL_NEEDS_USER_INPUT` is NOT set on `first-fixer-non-health`).

### Approach

- Classification lives at the launcher boundary (launchers already own auth/retry/sidecar interpretation via `external_auth_verdict`).
- Two NEW KVs (additive, no overload of `LAUNCHER_EXIT`).
- Bail routes through the EXISTING `run_ci_phase` `bail)` envelope (return non-zero from `run_ci_fix_vendor`; let outer flow handle exit 3).
- Policy fires only at the FIRST TIER (`cursor`); non-first tiers keep current waterfall.
- Infinite-loop guardrail (sentinel + counter, fail-closed write-before-attempt).
- Fork / unavailable-repo gate skips autonomous path.
- CI log capture with redaction so main-agent gets the actual failure and secrets stay out of context.
- `refresh-run-logs.sh` parity in the main-agent push path.

#2669 (BLOCKED_BY) lands first to allow this issue's BAIL_REASON token name to align with #2669's final exit-3 taxonomy. No production rollback is required if #2669 settles differently — the token may be renamed in a follow-up.

### Edge cases

1. Cursor success: `LAUNCHER_EXIT=0`, `CLASS=none`. No waterfall, no policy.
2. Missing/malformed `LAUNCHER_FAILURE_CLASS` in `$fail_file`: defaults to `health` (safer fallback). Bail-to-main-agent fires ONLY when KV explicitly says `other`.
3. `wrapper_rc=2` (launcher argv `die()`): launcher exits pre-emit-block; KV absent; defaults to `health` per #2; existing rollback + continue preserved. Policy does NOT fire.
4. Auth retry succeeded inside launcher: classification proceeds against post-retry result.
5. `/implement` main-agent fix succeeds, ship-pr.sh re-run succeeds: sentinel persists in `$IMPLEMENT_TMPDIR`; cleanup at tmpdir end.
6. `/implement` main-agent fix succeeds locally but CI still fails: second `ship-pr.sh` invocation either has the same first-fixer non-health failure (sentinel blocks a second attempt → user-bail) or the first fixer succeeds and fix lands.
7. Counter cap semantics: counter incremented BEFORE attempt; policy fires on read values 0/1/2 (attempts 1/2/3); 4th arrival sees `3` and falls through.
8. Sentinel/counter write failure: fail-closed → abort autonomous path, log Tool Failures, fall through.
9. `FORKED_TARGET` / `REPO_UNAVAILABLE`: skip autonomous path entirely.
10. Binary-missing detection: launcher's existing `command -v <binary>` precondition is the source; emit `health/binary-missing` before die.

### Failure modes

1. **Classification drift toward `other`**: misclassifies a transient health failure. Earliest signal: spike in `first-fixer-non-health` bails after a launcher change. Mitigation: narrow `health` set; Edge case #2 defaults unrecognized class to `health`; structural tests pin canonical tokens.
2. **Infinite re-invocation**: sentinel + counter design with fail-closed write-before-attempt ordering closes this. Mock-harness asserts 4th cycle falls through.
3. **Main-agent fix uses wrong diagnostic input**: addressed via gh-run-logs.sh capture (primary) + redacted launcher diagnostic (supplemental).

### Testing strategy

Extend `test-ship-pr.sh`, `test-launch-review.sh` (and direct launcher harnesses if present), and add focused mock harness for `/implement` Step 8+. Extend `test-implement-structure.sh` to assert new sub-steps and drop the prior anti-prose rule. Pin every canonical KV token literally so renames trigger structural test failures.

## Acceptance

- `LAUNCHER_FAILURE_CLASS` and `LAUNCHER_FAILURE_REASON` KVs are emitted by all three CI launchers using the canonical enums.
- `external_classify_launch_failure` helper in `lib-external-launcher-common.sh` is the single source of truth for the classification.
- `needs_user_bail_reason()` allowlist includes `first-fixer-non-health`.
- `run_ci_fix_vendor()` first-tier (`cursor`) non-health failure: state set, breadcrumb emitted, non-zero return; outer `run_ci_phase` `bail)` envelope runs the standard exit-3 sequence. `BAIL_NEEDS_USER_INPUT` is NOT set on this path.
- `wrapper_rc=2` continues to rollback + continue (existing behavior preserved).
- `/implement` Step 8+ Exit 3 branch on `BAIL_REASON=first-fixer-non-health` runs the 12-step autonomous fix sub-procedure: state-precondition gate (FORKED_TARGET / REPO_UNAVAILABLE skip), sentinel + counter guard, fail-closed write-before-attempt, gh-run-logs capture with redaction, Claude tool-call edit, relevant-checks, explicit `git add`, commit, `refresh-run-logs.sh`, push, re-invoke ship-pr.sh.
- Counter cap of 3 attempts; 4th arrival falls through to existing user-bail.
- `BAIL_FAILURE_DETAIL_LOG` content is redacted through `redact-secrets.sh` before reading; path validated to be under `$IMPLEMENT_TMPDIR`.
- All canonical KV tokens (`none`, `health`, `other`, `auth`, `binary-missing`, `health-probe`, `timeout`, `parse`, `refusal`, `unknown`) are present verbatim in helper + 3 launchers + ship-pr.sh guard, pinned by structural tests.
- `test-ship-pr.sh` covers the 7 scenarios listed under that file in "Files to modify/create".
- `test-implement-structure.sh` asserts the new Step 8+ sub-steps 1-12 and the prior anti-prose rule is dropped/inverted.
- Mock harness covers `/implement` Step 8+ loop edge cases (sentinel-exists, counter cap, sentinel write failure, missing FAILED_RUN_ID, FORKED_TARGET, REPO_UNAVAILABLE).
- Sibling `.md` contracts are updated for `lib-external-launcher-common.sh`, the three CI launchers, and `ship-pr.sh`.

diff_lines: 350

## Test plan
(no test plan section in plan-file)
