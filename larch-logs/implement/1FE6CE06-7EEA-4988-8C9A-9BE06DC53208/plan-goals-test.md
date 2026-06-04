## Goal
Implement issue #3413: [IMPLEMENTING] Re-enable /design run-log flush and fix its --admin merge gate (stuck PRs)\n\n# Re-enable /design run-log flush and fix its `--admin` merge gate.

## Implementation Plan
## Plan

# Implementation Plan — Re-enable /design run-log flush + fix the `--admin` merge gate (#3413)

## Files to modify/create

### UPDATED: `skills/design/scripts/design-publish.sh`

Reverse the #3378 disable so the end-of-run GitHub run-log flush runs again.

- Delete the forced-`PUBLISH_OK=true` stub block: the `# --- DESIGN RUN-LOG GITHUB FLUSH TEMPORARILY DISABLED (#3378) ---` comment plus the `if [[ -n "$SESSION_ID" ]]; then PUBLISH_OK=true; add_warn '...flush disabled pending migration to S3/R2...'; else add_warn '...SESSION_ID missing...'; fi`.
- Uncomment the real flush block directly below it (the `if [[ -n "$SESSION_ID" ]]; then ... "$PLUGIN_ROOT/scripts/design-log-publish.sh" --design-tmpdir ... --run-id "$SESSION_ID" --issue ... ; parse `PUBLISH_OK`; handle `SECRET_SCRUB_VIOLATIONS`; `append-tool-failure.sh` on the failure envelopes; else add_warn 'SESSION_ID missing' fi`).
- Drop the `TODO(s3-r2-migration)` comment.
- Net effect: on non-empty `SESSION_ID`, design-publish.sh invokes `design-log-publish.sh` and parses `PUBLISH_OK`. The `render-final-summary.sh --post-publish-only` step runs unconditionally after the publish attempt when `PLAN_WRITE_OK=true` — including on publish failures, so users receive refreshed diagnostics regardless of publish outcome (this is existing behavior, not a change). Only the `[DESIGNED]` rename and Step 6 cleanup remain gated on `PUBLISH_OK=true`. The empty-`SESSION_ID` branch still emits the `SESSION_ID missing` warning and skips publish. No other lines in this file change.

### UPDATED: `skills/design/scripts/design-publish.md`

Bring the design-publish contract doc back in sync with the live script behavior.

- Remove the stale #3378 temporary-disable language that says the GitHub run-log flush is skipped / forced successful.
- Document that, when `SESSION_ID` is present, `design-publish.sh` invokes `scripts/design-log-publish.sh` and consumes its `PUBLISH_OK` result.
- Document that `render-final-summary.sh --post-publish-only` runs unconditionally after the publish attempt when `PLAN_WRITE_OK=true` (including on publish failure), so users receive refreshed diagnostics regardless of publish outcome.
- Document that only the `[DESIGNED]` rename and Step 6 cleanup are gated on `PUBLISH_OK=true`.
- Document that missing `SESSION_ID` still skips the publish with a warning, and failed publish envelopes keep the existing failure-reporting behavior.

### UPDATED: `scripts/design-log-publish.sh`

Fix the merge gate so the flush PR reliably merges after required CI passes, instead of misreading the check-registration race as a CI failure (the confirmed stuck-PR root cause).

- Replace the single `ci_wait_out=$(gh pr checks "$PR_NUM" "${gh_repo_args[@]}" --required --watch --fail-fast 2>&1)` probe with a two-phase gate:
  - **Head binding (before the loop):** immediately after a successful push, capture `PUSH_HEAD_SHA=$(git -C "$WT_DIR" rev-parse HEAD)` (fail closed if empty). Each registration probe must treat checks as registered only when **both** (i) a parseable non-empty required-check JSON array is present **and** (ii) `gh pr view "$PR_NUM" "${gh_repo_args[@]}" --json headRefOid` reports a `headRefOid` equal to `PUSH_HEAD_SHA`. If checks are non-empty but the PR head OID does not match (stale checks from a prior force-push head), treat as **not registered** and keep polling — do not hand off to `--watch`. Reuse `with_transient_retry` / `redact_diagnostic` for `pr view` capture the same way as other `gh` calls in this script.
  1. **Registration wait (attempt-bounded):** add local constants near the gate, e.g. `REG_TIMEOUT=300`, `REG_INTERVAL=10`, and `REG_MAX_PROBES=$(( (REG_TIMEOUT + REG_INTERVAL - 1) / REG_INTERVAL + 1 ))` (inclusive initial probe at t=0 so the covered wall-clock window matches `REG_TIMEOUT`; cite #3413 and Codex-Pragmatic off-by-one), with a comment citing #3413 and the registration-race rationale. Poll for at most `REG_MAX_PROBES` probes until registered per the dual predicate above. On each probe, capture `gh pr checks "$PR_NUM" "${gh_repo_args[@]}" --required --json bucket` stdout under `set +e` — never under `set -e` or via a command substitution that propagates a non-zero exit code — and pipe the captured stdout to `jq` regardless of `gh`'s exit code, because `gh pr checks --json` can exit non-zero (e.g., rc=8 for pending checks) while still emitting valid non-empty JSON. Detect a non-empty checks array via `jq -e 'type=="array" and length>0' >/dev/null 2>&1` on the captured stdout (or assign to a variable and test `$?` / `[[ -n "$var" ]]`) — **never** let `jq -e` print `true` to stdout (that would violate the script's `KEY=value` stdout contract per BASH_AUTHORING). Do **not** use English "no checks reported" string matching and do **not** rely on `gh`'s exit code alone as the registration signal. Sleep only between probes, never after the final probe, with `"${SLEEP_SCRIPT_DIR:-$SCRIPT_DIR}/sleep-seconds.sh" "$REG_INTERVAL" >/dev/null 2>&1 || sleep "$REG_INTERVAL"` (the same overridable idiom `lib-net.sh` already uses; this script already sources `lib-net.sh`). Do not add an env var.
  2. **Completion watch:** once registered (dual predicate satisfied), hand off to the existing `gh pr checks "$PR_NUM" "${gh_repo_args[@]}" --required --watch --fail-fast` wait, then the existing `with_transient_retry ... gh pr merge "${gh_repo_args[@]}" "$PR_NUM" --squash --admin --delete-branch`.
- Fail closed in three cases: (a) required checks never register within the attempt budget / grace (including head never matching `PUSH_HEAD_SHA`) → `larch_err` a **dedicated** registration-timeout message (e.g. `required CI checks did not register within ${REG_TIMEOUT}s` and include probe count / `REG_MAX_PROBES`), run `redact_diagnostic` on the last captured `--json` stdout (and last `pr view` diagnostic if useful), set `merge_rc=1`, and **do not** call `--watch` (distinct from watch-failure wording so operators do not mislabel a registration race as CI failure); (b) `--watch --fail-fast` returns non-zero (a required check failed) → keep the existing refuse-to-merge path that sets `merge_rc="$ci_rc"` with the existing `required CI checks did not pass` diagnostic; (c) `PUSH_HEAD_SHA` / `pr view` capture failures that persist through the budget → same registration-timeout path as (a). Keep `--admin` (not `--auto`).
- Reuse the existing `redact_diagnostic` helper for any captured-output diagnostics.

### UPDATED: `scripts/design-log-publish.md`

- Update the merge-gate description so it states the gate waits for required checks to register **for the pushed head** before watching them, treats "no required checks reported yet" and "checks reported for a stale PR head" as transient wait rather than CI failure, and uses a fixed probe budget derived from the timeout/interval constants (`ceil(timeout/interval)+1` probes) so tests can stub sleep without waiting on wall-clock time.
- Document that the registration probe captures stdout under `set +e` and treats a non-empty JSON array as "registered" regardless of `gh`'s exit code (e.g., pending checks may return non-zero rc with valid JSON), with `jq -e` redirected to `/dev/null` (or captured in a variable) so boolean output never leaks onto the script's stdout contract stream.
- Document the dual registration predicate (`headRefOid` must equal the post-push `PUSH_HEAD_SHA` **and** required-check JSON non-empty) so pause/recovery force-push reuse cannot merge on stale green checks from the prior head.
- Document the dedicated registration-timeout `larch_err` (include `REG_TIMEOUT` / probe budget), `redact_diagnostic` on last capture, `merge_rc=1`, and explicit **no `--watch`** on that path — distinct from the watch-failure `required CI checks did not pass` diagnostic.
- Document that the gate still fails closed when a required check fails OR when checks never register (or head never matches) within the bounded grace. Keep the `--admin` (not `--auto`) rationale. Describe behavior, not line numbers (per the drift-prone-prose rule).

### UPDATED: `SECURITY.md`

Document the security-relevant admin-merge gate change.

- Update the `/design` run-log publish / admin-merge paragraph to say required checks must first register **for the pushed commit head** within a bounded grace / probe budget before the script watches them (stale prior-head check state does not satisfy registration).
- State that required-check failures, registration-timeout (non-registration or head mismatch within the budget), and watch failures all refuse the merge (`PUBLISH_OK=false`, PR left open for diagnosis); registration-timeout uses a dedicated operator message distinct from CI-failure wording (`did not register within` vs `did not pass`).
- State that only after registration plus successful required-check watch does the script perform the existing `gh pr merge --squash --admin --delete-branch`; keep the rationale that `--admin` is intentional and not an unconditional bypass.

### UPDATED: `skills/design/scripts/test-design-publish.sh`

Re-enable the gated cases that assert design-publish.sh's handling of the now-live `design-log-publish.sh` invocation. The harness already carries the `design-log-publish.sh` stub and `PUBLISH_*` knobs for this.

- Flip the `if false; then ... fi` guard (the `# --- DISABLED pending S3/R2 run-log migration (#3378) ---` block) to active so the three failure-envelope cases run again: `PUBLISH_OK=false`, nonzero-without-KV, and exit-0-without-KV.
- Restore the happy-path assertions: assert `design-log-publish` IS invoked (remove the "should be skipped" inversion), restore the call-log ordering to plan → marker → upsert → publish, and keep the `PUBLISH_OK=true`-from-stub assertion.
- Restore the exit-3 case's `PUBLISH_LOG` (publish ran) assertion alongside the existing rename-log assertion.
- For `PUBLISH_OK=false` and other failure-envelope cases, assert observable behavior in this harness only: `render-final-summary.sh --post-publish-only` IS called (it runs unconditionally when `PLAN_WRITE_OK=true`), and `tracking-issue-write` rename is NOT called. Do not assert Step 6 cleanup — `design-publish.sh` does not invoke cleanup; the harness has no cleanup stub or log to observe it.
- Remove the `(#3378)`-disabled comment markers that referenced the temporary skip.

### UPDATED: `scripts/test-design-log-publish.sh`

Add regression coverage for the merge-gate fix using the existing PATH-injected `gh` stub.

- Extend the `gh` stub to handle `pr checks` with a clear split between two probe shapes. The stub must branch on `--json` first:
  - When `pr checks` arguments include `--json`: return a JSON array string and exit 0. When no delay knobs are set, the default is a minimal non-empty required-check array (e.g. `[{"name":"ci","bucket":"pass"}]`). This default ensures existing happy-path, pause, recovery, merge-fail, and CI-fail harness cases all pass the registration phase without behavioral change — they rely on this default and need no further modification beyond the stub split. Reserve `[]` (empty array) only for the explicitly-configured never-registered and registration-race cases.
  - When `pr checks` arguments include `--watch` (and `--fail-fast`): use the existing `GH_STUB_CHECKS_RC`/`GH_STUB_CHECKS_OUT` knobs. These knobs must NOT affect `--json` registration probes. Fail unhandled `pr checks` shapes to catch wiring mistakes.
  - Add a probe counter so the first K `--json` probes return `[]` then a populated array (for the race case). Point `SLEEP_SCRIPT_DIR` at a no-op `sleep-seconds.sh` stub so the poll runs instantly.
- Extend the `gh` stub `pr view` arm for `--json headRefOid` (and compound calls that include `headRefOid`):
  - **Default OID derivation (FINDING_3):** when `GH_STUB_PR_HEAD_OID` is unset, resolve the pushed head OID from the harness clone — not a hard-coded placeholder. Prefer `TEST_MERGE_BRANCH` when set (matches `export TEST_MERGE_BRANCH="larch-log-design-<run-id>"` in cases that exercise merge); otherwise parse the most recent `pr create` invocation from `GH_STUB_LOG` and extract the `--head <branch>` token, then `git -C "${TEST_CLONE_ROOT}" ls-remote origin <branch>` (first field = OID). If `TEST_CLONE_ROOT` is unset or ls-remote is empty, fail the stub loudly (exit 98) so miswired cases surface immediately rather than timing out in registration.
  - **Override:** `GH_STUB_PR_HEAD_OID` (and `GH_STUB_PR_HEAD_OID_MISMATCH=1` or a first-N mismatch knob) return a stale OID for the first registration probes while `--json` checks are already non-empty — regression for pause reuse / force-push stale-check acceptance (#3413 / Codex-Edge).
  - Non-`headRefOid` `pr view` shapes (e.g. `--json url`) keep today's behavior.
- **Update the existing `=== required CI check failure ===` block** (today: `GH_STUB_CHECKS_RC=8` only asserts `PUBLISH_OK=false` and no merge): after the registration-phase default (`--json` non-empty + aligned `headRefOid`), configure the stub so `--watch --fail-fast` returns non-zero (keep `GH_STUB_CHECKS_RC=8` / `GH_STUB_CHECKS_OUT` on the **watch** arm only). Assert stderr (capture publish stderr to a file in the case, not `/dev/null`) contains the existing watch-failure substring `required CI checks did not pass` and does **not** contain the registration-timeout substring `did not register within`. Assert `grep -q 'pr checks' "$GH_STUB_LOG"` includes a line with `--watch` (watch path exercised). Assert no `gh pr merge`. This distinguishes case 3 from never-registered / head-mismatch timeouts.
- Assert the registration loop is attempt-bounded: the never-registered case should exhaust `REG_MAX_PROBES` derived as `ceil(REG_TIMEOUT/REG_INTERVAL)+1` (31 for 300/10) without sleeping after the final probe, so the no-op sleep stub makes the case fast without introducing any env override for production constants.
- **Registration-timeout watch-skip assertions (FINDING_4):** in the never-registered case (case 2) and the stale-head never-aligns variant (case 5b), assert `GH_STUB_LOG` contains `pr checks` with `--json` but **no** line matching `pr checks` with `--watch` (e.g. `grep -q 'pr checks' && grep 'pr checks' ... | grep -q -- '--watch'` must fail / use negated grep). Complements the stderr registration-timeout substring assertion.
- New cases:
  1. **Registration race:** first K `--json` probes return `[]`, then non-empty; aligned `headRefOid`; `--watch` returns 0 → assert `PUBLISH_OK=true` and `gh pr merge ... --admin` ran.
  2. **Never registered:** every `--json` probe returns `[]` within the grace → assert `PUBLISH_OK=false`, no `gh pr merge`, stderr mentions `did not register within`, no `--watch` in `GH_STUB_LOG`.
  3. **Required check fails:** `--json` non-empty (registered), `--watch` returns non-zero → assert `PUBLISH_OK=false`, no `gh pr merge`, stderr `did not pass` and not `did not register within` (same assertions as the updated existing CI-fail block).
  4. **Registration with non-zero rc:** `--json` returns a non-empty pending array and exits non-zero (e.g., rc=8); `--watch` returns 0 → assert `PUBLISH_OK=true` and `gh pr merge ... --admin` ran. Regression for `set +e` / parse-regardless-of-rc requirement.
  5. **Stale head on reuse:** seed an open PR + force-push path (reuse existing pause-reuse fixture pattern), configure first `--json` probes to return non-empty pass checks while `pr view` `headRefOid` mismatches `PUSH_HEAD_SHA` (via mismatch knob), then align head OID and checks → assert `PUBLISH_OK=true` and merge only after head match; **5b:** head never aligns within the budget → `PUBLISH_OK=false`, no merge, stderr registration-timeout (not watch failure), no `--watch` in `GH_STUB_LOG`.

## Approach

- Keep the fix local to the flush path. Do NOT reuse `ci-wait.sh` / `ci-status.sh` — they carry `/implement` rebase, behind-count, and fix-attempt semantics that are wrong for a logs-only `--admin` flush PR. Borrow only the robust JSON-count idiom (the `bucket` field) those scripts already use.
- "Reported" = required-check JSON array non-empty AND parseable **and** PR `headRefOid` equals the post-push `PUSH_HEAD_SHA`, regardless of `gh pr checks --json` exit code. Capture stdout under `set +e`; do not rely on rc as a registration signal. Use `jq -e ... >/dev/null 2>&1` (or a variable capture) so successful probes never emit boolean stdout on the contract stream.
- The two-phase gate (register for current head, then watch) is the minimal change: it adds an attempt-bounded pre-poll (`ceil(timeout/interval)+1` probes), a head-binding guard, a dedicated registration-timeout diagnostic (no `--watch`), and leaves the existing `--watch --fail-fast` wait and the `--admin` squash merge untouched.
- Re-enabling the flush is a pure revert of #3378's two-block swap; the surrounding tail behavior — render unconditional on `PLAN_WRITE_OK`, rename and cleanup gated on `PUBLISH_OK` — already exists and does not change.
- Harness fidelity: default `headRefOid` tracks the branch the publish script actually pushed (`TEST_MERGE_BRANCH` or last `pr create --head` in `GH_STUB_LOG` + `ls-remote`), so registration succeeds in existing cases without per-case OID boilerplate; explicit knobs only for mismatch/stale-head scenarios.

## Edge cases

- Repo with zero required checks → array never non-empty → fail closed after the probe budget with the registration-timeout diagnostic (preserves today's "no required checks → fail closed" intent; distinct stderr from watch failure).
- Checks already green at the first probe → array non-empty → `--watch` returns 0 immediately → merge.
- Pause/recovery reuses an open PR and force-pushes a new head → first probes may show non-empty pass checks for the **old** head while `headRefOid` ≠ `PUSH_HEAD_SHA` → treated as not registered until GitHub reports checks for the new head and head OID matches (prevents merging before new CI runs).
- A required check already failed during the grace → array non-empty → `--watch --fail-fast` returns non-zero → fail closed with `did not pass` (not registration-timeout).
- `gh pr checks --json` returns non-empty JSON with non-zero rc (e.g., pending checks at rc=8): treated as registered (array non-empty, stdout parsed regardless of rc), proceeds to `--watch`. This is the correct behavior — non-zero rc from `--json` does not mean failure.
- Empty `SESSION_ID` → publish is skipped entirely (unchanged), so the gate is never reached.
- `jq` missing → `jq -e` fails → treated as not-reported → fail closed after the derived probe budget / grace (degenerate environment; `jq` is a repo-wide dependency already used by sibling CI helpers).
- Harness without `TEST_CLONE_ROOT` / branch resolution → stub fails fast (exit 98) instead of silent registration-timeout, surfacing miswired tests.

## Failure modes

- Grace too short on a slow GitHub: required checks register after the probe budget / grace → false fail-closed (PR left open, `PUBLISH_OK=false`). Earliest signal: the dedicated registration-timeout `larch_err` (e.g. `required CI checks did not register within ${REG_TIMEOUT}s`, includes probe budget; **not** the watch-failure `did not pass` string). Mitigation: the 300s grace (31 probes at 10s) is generous against typical seconds-scale registration, the derived probe count keeps tests fast with a no-op sleep stub, and the constants are a one-line tune. Strictly better than today's zero-grace first-probe failure.
- Stale-head false merge (pre-fix): non-empty checks for an old head while force-push updated the branch → mitigated by head-binding; signal if miswired: merge before new CI — regression case 5 guards this.
- Flaky required check: fails closed by design. Signal: the existing refuse-to-merge stderr with `did not pass` and the failed-check diagnostic. Mitigation: re-invoke `/design` (the publish tail is idempotent) or rerun CI.
- `gh pr checks --json` transient network error: empty stdout → `jq` parse fails → treated as not-reported → keeps polling within the probe budget / grace (self-heals); only fails closed if it persists for every probe.
- Regression conflation: registration-timeout and watch-failure share `PUBLISH_OK=false` + no merge — mitigated by distinct stderr substrings, `--watch` absent from stub log on timeout paths, and explicit watch-failure stderr assertion on the CI-fail / case-3 paths.

## Testing strategy

- `scripts/test-design-log-publish.sh`: 5 new gate cases (registration race, never-registered, real failure, non-zero-rc-with-pending-JSON, stale-head on force-push reuse) via the `gh` stub + no-op `SLEEP_SCRIPT_DIR`; assert `PUBLISH_OK`, whether `gh pr merge` ran, stderr distinguishes `did not register within` vs `did not pass`, and (timeout paths) `GH_STUB_LOG` has no `pr checks ... --watch`. The stub must split `--json` and `--watch` arms so `GH_STUB_CHECKS_RC`/`GH_STUB_CHECKS_OUT` only affect `--watch --fail-fast` invocations; default `--json` non-empty **and** default `pr view headRefOid` derived from `TEST_MERGE_BRANCH` or last `pr create --head` + `git ls-remote` on `TEST_CLONE_ROOT` so existing cases are unaffected.
- **Update existing `=== required CI check failure ===` block:** capture stderr; assert `did not pass`, not `did not register within`; assert `--watch` ran in `GH_STUB_LOG`; assert no merge (FINDING_2).
- `skills/design/scripts/test-design-publish.sh`: re-enable the 3 previously-gated failure-envelope cases, restore the happy-path "publish invoked" + ordering assertions, restore the exit-3 publish assertion, and on publish failure assert `render-final-summary.sh --post-publish-only` runs unconditionally when `PLAN_WRITE_OK=true` and that `tracking-issue-write` rename is not invoked — do not add Step 6 cleanup assertions (not observable in this harness).
- Run `bash scripts/relevant-checks.sh` (or `make lint`) after edits; the `test-design-publish` and `test-design-log-publish` harnesses must pass.
- Manual / CI acceptance: a real `/design` run produces a `larch-logs/design/<run-id>/` PR that registers required CI, passes, and squash-merges with `--admin` with its branch deleted.
- Documentation acceptance: `skills/design/scripts/design-publish.md`, `scripts/design-log-publish.md`, and `SECURITY.md` no longer describe the #3378 forced-success disabled state and accurately document the bounded registration wait (inclusive probe count), head-bound registration, dedicated registration-timeout stderr, `set +e` JSON capture, rc-independent checks parsing, jq stdout hygiene, and fail-closed admin-merge gate.

## Acceptance

- After a `/design` run with the flush re-enabled, the `larch-logs/design/<run-id>/` PR is created, required CI runs and passes, and the PR is squash-merged with `--admin` and its branch deleted.
- No flush PR is left stuck open because the gate polled before required checks registered: "no required checks reported yet" within the bounded probe budget is a transient wait, not a CI failure.
- The merge is bound to the pushed head: checks count as registered only when the required-check JSON array is non-empty AND the PR `headRefOid` equals the post-push `PUSH_HEAD_SHA`. Stale prior-head checks (pause / force-push reuse) never satisfy registration.
- The gate fails closed (`PUBLISH_OK=false`, PR left open, no merge) in all three cases: a required check fails (`--watch --fail-fast` non-zero), required checks never register within the budget, or the head never matches within the budget. The registration-timeout path uses a dedicated message (`did not register within`) distinct from the watch-failure message (`did not pass`), and never invokes `--watch`.
- `--admin` (not `--auto`) is preserved; the gate is not an unconditional bypass.
- The registration probe captures `gh pr checks --required --json bucket` stdout under `set +e` and treats a non-empty array as registered regardless of `gh`'s exit code (e.g. rc=8 pending); `jq -e` output never leaks onto the script's `KEY=value` stdout contract stream.
- `skills/design/scripts/test-design-publish.sh`: the #3378-gated failure-envelope cases are re-enabled and pass; the happy path asserts the flush IS invoked in plan → marker → upsert → publish order.
- `scripts/test-design-log-publish.sh`: the five merge-gate cases (registration race, never-registered, required-check failure, non-zero-rc-with-pending-JSON, stale-head reuse) pass with a no-op `SLEEP_SCRIPT_DIR`; the existing CI-fail block asserts the watch path ran and stderr says `did not pass`, not `did not register within`.
- `skills/design/scripts/design-publish.md`, `scripts/design-log-publish.md`, and `SECURITY.md` no longer describe the #3378 forced-success disabled state and accurately document the bounded head-bound registration wait and the fail-closed admin-merge gate.
- `bash scripts/relevant-checks.sh` (or `make lint`) passes, including the two re-enabled/extended harnesses.

diff_lines: 435

## Test plan
(no test plan section in plan-file)
