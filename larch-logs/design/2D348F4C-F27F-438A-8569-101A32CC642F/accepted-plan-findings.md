### FINDING_1: Plan references run_recovery_waterfall but symbol absent on main
- **Concern**: Plan (line 28, 37, 65) tells implementers to mirror or reuse run_recovery_waterfall, but that function does not exist anywhere in `scripts/ship-pr.sh` on current main. It is part of the #2395 plan (still [IMPLEMENTING]). Implementers cannot validate "mirror" semantics by grep against current code. Raised by 6 reviewers: Cursor-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Pragmatic, Codex-Requirements.
- **Proposed resolution**: After #2395 merges (which is the documented blocker), pin the concrete function name and `scripts/ship-pr.sh` line range that ship in #2395. Alternatively, paste the exact rollback algorithm (delta computation + `--` sentinel + while-read loop) inline in the plan so implementers do not need to grep for the helper. The "blocked by #2395" note is necessary but not sufficient.


### FINDING_10: Backoff comment stale after `_max_fix` reduction
- **Concern**: `scripts/ship-pr.sh:1353-1354` comment documents the full 2s/4s/8s/16s ladder; under `_max_fix=3`, only the first two ladder steps fire. Raised by 1 reviewer: Cursor-Arch.
- **Proposed resolution**: Update the comment in the same edit as the `_max_fix=5→3` change: "Jittered backoff: 2s/4s ±25% (8s/16s entries reserved for higher _max_fix values; unused at _max_fix=3)."


### FINDING_11: Forwarding raw `gh-run-logs.sh` capture to external launchers widens secret-exposure surface
- **Concern**: `scripts/gh-run-logs.sh:41-55` emits unstructured failed CI log text that can contain secrets, internal URLs, PII, or private hostnames. Forwarding raw to Cursor/Codex/Claude via `--failure-log` crosses an external-tool trust boundary that today's launcher contracts do not protect via `redact-secrets.sh`. SECURITY.md (line 124) does not currently document this surface. Raised by 4 reviewers: Cursor-Arch, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements.
- **Proposed resolution**: Run the captured `gh_logs_fail_file` through `scripts/redact-secrets.sh` (and possibly `scripts/redact-tmpdir-paths.sh`) before passing to `--failure-log`. Add a regression test with a fake `sk-*` / `ghp_*` token in CI log content; assert it does not appear in `launcher-calls.txt`. Update SECURITY.md to document `--failure-log` as a redaction-required surface.


### FINDING_13: `fail_file` name collision in plan's proposed signature change
- **Concern**: Plan says "extend `run_ci_fix_vendor`'s signature with a third positional `gh_logs_fail_file=$3` argument" and the call site `if run_ci_fix_vendor "$phase" "$failed_run" "$fail_file"; then` — where the caller's `$fail_file` at line 1330 IS the gh-run-logs capture. Inside `run_ci_fix_vendor`, `fail_file` is reassigned multiple times via `failure_capture_path "$phase"` for per-tier launcher captures. Reusing the same name in caller and callee with different lifetimes is fragile. Raised by 2 reviewers: Cursor-Edge, Codex-Requirements.
- **Proposed resolution**: In `run_evaluate_failure`, immediately after the `gh-run-logs.sh` line at 1330, assign a dedicated local: `local gh_logs_capture="$fail_file"; fail_file=""`. Pass `"$gh_logs_capture"` to `run_ci_fix_vendor`. Inside `run_ci_fix_vendor`, accept it as `local gh_logs_capture=$3` (not `gh_logs_fail_file`). The two functions never share the variable name.


### FINDING_14: Citation off-by-one — post-success starts at 1245, not 1244
- **Concern**: Plan line 30 says "On `rc=0`, `break` … and fall through to the existing post-success code at line 1244+". But `scripts/ship-pr.sh:1244` is `[ "$rc" -eq 0 ] || return 1` — the rc-guard. The post-success pipeline (`append-token-record.sh`, dirty-path capture, etc.) starts at line 1245. Raised by 1 reviewer: Codex-Requirements.
- **Proposed resolution**: Replace "line 1244+" with "lines 1245-1307" throughout the plan. The success gate at 1244 stays as-is; only the citation prose changes.


### FINDING_15: Plan should explicitly delete the inner `for vendor_attempt in 1 2 3` loop
- **Concern**: Plan section "## Approach" describes the new tier list but does not explicitly say "the existing `for vendor_attempt in 1 2 3; do … done` block at lines 1225-1244 is REMOVED, not nested under the new tiers." An implementer might keep the inner loop and nest tiers, doubling launcher calls. Raised by 1 reviewer: Codex-Requirements.
- **Proposed resolution**: Add a bullet at the top of the "## Approach" section: "Delete the existing `for vendor_attempt in 1 2 3; do … done` block at lines 1225-1244 entirely. The new tier sequence REPLACES it, not wraps it."


### FINDING_17: `gh-run-logs.sh` capture happens once before outer loop — stale across outer retries
- **Concern**: `scripts/ship-pr.sh:1329-1361` — `gh-run-logs.sh` runs once before the outer `while` loop. Every outer retry reuses the same capture path. If local tree state and remote CI state diverge between outer attempts (e.g., after a successful fix push that's still propagating), the cached log is stale. Raised by 1 reviewer: Cursor-Edge.
- **Proposed resolution**: Two options — (a) refresh `gh-run-logs.sh` at the start of each outer attempt (extra API calls but accurate context); (b) document the intentional staleness with a test pinning it. Pick one in the plan and state the rationale.


### FINDING_18: Submodule state not captured by `capture_tracked_dirty_paths`
- **Concern**: `scripts/ship-pr.sh:50-55` `capture_tracked_dirty_paths` uses `git diff --name-only HEAD` which reports the gitlink for a dirty submodule but does not capture the submodule's inner state. Rollback via `git checkout -- <gitlink>` resets to the pinned SHA but does not restore submodule worktree state, leaving hidden corruption. Raised by 1 reviewer: Cursor-Edge.
- **Proposed resolution**: Either extend rollback inputs with submodule-aware logic (`git submodule update --force --checkout`) matching whatever #2395 ships, OR explicitly document that submodule-modifying CI-fix attempts are out of scope for the rollback contract. Add an exclusion line to the rollback description.


### FINDING_19: New `fix-loop-3tier` section would not run under existing Makefile target
- **Concern**: Plan optionally mentions creating a new `fix-loop-3tier` section in `scripts/test-ship-pr.sh`. The Makefile target `test-ship-pr-fix-loop` (Makefile:449-450) calls `bash scripts/test-ship-pr.sh --section fix-loop` — a `fix-loop-3tier` section name would not match, so the new tests would skip silently under CI. Raised by 3 reviewers: Codex-Innovation, Codex-Pragmatic, Codex-Requirements.
- **Proposed resolution**: Add an explicit instruction to the plan: "EXTEND the existing `fix-loop` section. Do NOT create a separate `fix-loop-3tier` section." This avoids the Makefile/shard wiring churn entirely. If a separate section is genuinely needed (size / readability), the plan must also list edits to Makefile:449-450, harness shards, docs/linting.md, and the `--section` header block in `scripts/test-ship-pr.sh:411-416`.


### FINDING_2: Rollback baseline contradiction (per-tier snapshot vs function-entry snapshot)
- **Concern**: Plan rollback prose (lines 36-37 and 46-47) contains two contradictory statements: "Before the failed tier runs, snapshot dirty tracked paths via …" (per-tier snapshot model) AND "The pre-Cursor snapshot is taken once at function entry (before Tier 1), so each rollback delta is relative to the per-function entry baseline" (single-snapshot model). These describe different rollback semantics. Raised by 5 reviewers: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Codex-Pragmatic, Codex-Requirements.
- **Proposed resolution**: Pick the conservative single-baseline model (snapshot once at function entry; every tier delta is computed against that one baseline). Delete the per-tier snapshot bullet. Update test case `ci_fix_vendor_rollback_restores_failed_tier_dirty_paths` to pin this specific contract.


### FINDING_20: Plan contradiction — "inline (no extraction)" vs "reuse #2395's tested rollback helper"
- **Concern**: Plan synthesis line 14 says "stays inline (no extraction of a shared helper) because the verifier model differs". Failure-modes mitigation line 1.M says "reuse #2395's tested rollback helper directly (do not reinvent the path-delta computation)". These contradict: either the rollback algorithm is inline (paste) or it calls a helper. Raised by 1 reviewer: Cursor-Innovation.
- **Proposed resolution**: Pick one model. Recommendation: name a concrete `_rollback_paths` helper that #2395 ships (or rename one of its inner blocks to that name as a follow-up to #2395) and have `run_ci_fix_vendor` call it. This avoids duplicated, divergent delta math.


### FINDING_22: rc=3 ("in-progress") path semantics underspecified
- **Concern**: `gh-run-logs.sh:17-19` defines rc=3 as "run still in progress". The plan's edge-case section frames rc=3 like "benign empty capture" and proceeds to dispatch tiers anyway. If the CI run is still in progress, dispatching vendors to fix a not-yet-failed run is pointless and burns tokens. Raised by 1 reviewer: Cursor-Edge.
- **Proposed resolution**: Three options — (a) on rc=3, skip the entire `run_ci_fix_vendor` call this outer attempt and let the backoff sleep before retry (preferred — wait for CI to finish); (b) on rc=3, dispatch tiers anyway with no `--failure-log` (current plan); (c) on rc=3, exit with a fresh stall token like `10-ci-in-progress` and let `/implement` retry. Plan should pick one and pin it with a test.

## Out-of-scope observations (vote YES = file as separate GitHub issue, NO = drop, EXONERATE = neutral)


### FINDING_3: Tier success/failure keys off wrapper rc but CI launchers exit 0 on agent failure
- **Concern**: `scripts/launch-cursor-ci.sh:193-196` and `scripts/launch-codex-ci.sh:175-178` emit `LAUNCHER_EXIT=<n>` on stdout and then `exit 0` for agent runtime failures (auth, timeout, model error). The plan's tier success check uses `rc=$?` which would treat agent failure as tier success — the cascade never falls through to Codex/Claude, and the post-success commit/push runs after a failed fix. Raised by 4 reviewers: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic.
- **Proposed resolution**: Capture launcher stdout (`>"$fail_file" 2>&1` already does this), parse `LAUNCHER_EXIT=<n>` from the fail_file content, and treat tier success as `wrapper_rc == 0 AND launcher_exit == 0`. Keep wrapper rc=2 (validation failure) as tier failure. Add a regression test: launcher stub exits wrapper 0 but emits `LAUNCHER_EXIT=124`; assert the next tier runs.


### FINDING_4: `[ -s "$gh_logs_fail_file" ]` is not a valid "useful CI log" guard
- **Concern**: `scripts/gh-run-logs.sh:41-55` writes a URL header line before discovering whether failed-step logs are actually available. On rc=3 ("run still in progress" per `gh-run-logs.sh:17-19`), the file is non-empty but contains only the header — `[ -s file ]` passes and the misleading capture is forwarded to all tiers. Same issue on rc=1 (gh API failure with the header already written). Raised by 5 reviewers: Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-Pragmatic.
- **Proposed resolution**: Capture `gh-run-logs.sh`'s rc separately in `run_evaluate_failure` and pass it as a fourth positional argument (or in a state variable) to `run_ci_fix_vendor`. Forward `--failure-log` only when `gh_logs_rc == 0`. Add tests for the rc=3-with-header-only and rc=1-with-header-only cases.


### FINDING_5: Existing fix-loop tests pin 5 outer attempts / 20 checks — plan does not update them
- **Concern**: `scripts/test-ship-pr.sh:2440-2481` `ci_fix_exhausted` asserts `check_count -eq 20` (= 5 outer × 4 checks per attempt) and the message "all 5 vendor attempts"; `scripts/test-ship-pr.sh:2232-2287` `ci_fix_vendor_retry` asserts exactly 3 launcher lines (matching the current inner 3-vendor-attempt loop). After `_max_fix=3` + 3-tier waterfall, both literals desynchronize and `make test-ship-pr-fix-loop` will fail. Plan's testing section adds 11 new cases but does not list updates to these existing cases. Raised by 6 reviewers: Cursor-Arch, Cursor-Innovation, Codex-Pragmatic, Cursor-Pragmatic, Codex-Requirements, Cursor-Requirements.
- **Proposed resolution**: Add explicit bullets to the testing section: (a) revise `ci_fix_exhausted` to expect 3 outer attempts × 4 checks = 12 (or whatever the new math is) and update assertion strings; (b) revise `ci_fix_vendor_retry` to expect 3 launcher lines (one per tier) per outer attempt, not three calls to the same vendor. Either fold these into the existing `fix-loop` section or document the migration.


### FINDING_6: `make_repo` case-arm missing `launch-claude-ci.sh` — Claude argv not logged in tests
- **Concern**: `scripts/test-ship-pr.sh:172-217` `write_stubs` and the `case` arm in `make_repo` only match `launch-cursor-ci.sh|launch-codex-ci.sh` for the `SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt` log. New tier-order tests that grep that file would silently miss Claude invocations. Raised by 3 reviewers: Cursor-Arch, Cursor-Edge, Codex-Innovation.
- **Proposed resolution**: Add `launch-claude-ci.sh` to the `write_stubs` loop and to the `case` arm at `scripts/test-ship-pr.sh:172-217` (and the duplicate fixture block at `:2387-2406`) so Claude argv appends to `launcher-calls.txt` like the other launchers. State this in the plan's `## Testing strategy` as a pre-requisite step.


### FINDING_7: Shared `$output` path across tiers leaks token-record sidecars
- **Concern**: `scripts/ship-pr.sh:1220-1246` uses one `$output` basename for all tiers. After a failed Cursor tier, `${output}.token-record` may exist; a later successful Codex/Claude tier that does not write a token record (or writes a different one) causes `append-token-record.sh` to ingest stale token data from the failed tier. Raised by 2 reviewers: Codex-Edge, Codex-Innovation.
- **Proposed resolution**: Use per-tier output basenames (e.g., `${output}.cursor`, `${output}.codex`, `${output}.claude`) and pass the winning tier's basename to `append-token-record.sh`. Alternatively, `rm -f "${output}.token-record"` between tier attempts. Add a regression: failed Cursor leaves `${output}.token-record`, Codex succeeds without writing a token record; assert no stale tokens are appended.


### FINDING_8: Path-only rollback cannot preserve pre-existing dirty tracked content
- **Concern**: `git restore --staged` + `git checkout` rolls files back to HEAD. If a file was already dirty at function entry (operator's in-progress edits), and a failed tier modifies it, path-delta rollback either contaminates the next tier (if the file is excluded from the delta) or destroys operator work (`git checkout --` restores HEAD, losing operator's dirty content). Raised by 3 reviewers: Codex-Edge, Codex-Innovation, Cursor-Pragmatic.
- **Proposed resolution**: Three options listed by reviewers — (a) require a clean tracked baseline at `run_ci_fix_vendor` entry (fail-closed if dirty); (b) snapshot exact pre-tier content with `git stash --keep-index` or `git diff > patch_file`; (c) run each tier in a disposable worktree and apply only the winning tier's patch. The plan should pick one and pin it. Add regression: pre-existing dirty tracked file is preserved exactly across a failed-then-successful tier sequence.


### FINDING_9: Rollback misses staged-added new files
- **Concern**: A failed Cursor tier can `git add <new_file>`. After `git restore --staged` the file becomes untracked, but it was NOT in the pre-tier untracked snapshot (it was created by the tier), so it survives into the Codex/Claude tier. Raised by 1 reviewer: Codex-Arch.
- **Proposed resolution**: Capture staged-added paths as a third class alongside tracked/untracked deltas. After `git restore --staged`, also `rm -f --` the now-untracked paths the failed tier introduced via `git add`. Add regression: failed tier stages a brand-new file; assert it is gone before the next tier runs.


