# Review Round 2

- Mode: `diff`
- 10 accepted, 8 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: Merge-retry continuations can bypass the iteration cap
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The merge-retry path can loop past the session iteration cap because cap enforcement moved into the non-merge branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reapply cap at loop entry for merge-retry continuations or check cap immediately after ci_not_ready/main_advanced increment


### FINDING_11: Fresh fallback can retain stale PR identity in context/state
- **Reviewer(s)**: dyn-github-pr-output.txt
- **Severity**: important
- **Concern**: `_hydrate_fresh_context()` leaves `ctx.pr_number` / `ctx.pr_url` intact after `_resume_plan()` degrades to fresh, creating a window where persisted state disagrees with GitHub ground truth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-github-pr-output.txt: Clear `pr_number`/`pr_url` (and optionally `merge_result`/`pr_closed`) in `_hydrate_fresh_context`, or hydrate them from the `ResumePlan` (`pr_number=None`, `pr_url=""`) whenever `start == "fresh"`.


### FINDING_14: Legacy PHASE=done can skip required postmerge recovery
- **Reviewer(s)**: dyn-postmerge-flow-output.txt
- **Severity**: important
- **Concern**: Normal-repo resume treats `PHASE=done` plus GitHub `MERGED` as terminal success, but legacy state may have written `PHASE=done` even when postmerge did not complete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-postmerge-flow-output.txt: When GitHub reports `MERGED`, only classify `start="done"` if postmerge completion is corroborated (for example `run_logs.manifest_status(ctx) == config.MANIFEST_STATUS_DONE`, and/or `post-merge-sentinel` plus a non-stalled finalize snapshot); otherwise keep routing to `merged` so postmerge is retried even when stale local `PHASE=done` is present.


### FINDING_17: State REPO is not validated before GitHub operations
- **Reviewer(s)**: dyn-state-io-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `REPO` from the state file is hydrated and passed into GitHub operations without owner/repo slug validation or equality checks against `ctx.repo`, enabling state-file-controlled repo redirection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-io-output.txt: Validate `REPO` with the same slug rules used elsewhere (e.g. `report_tokens_scan._valid_repo_slug`), reject values starting with `-`, and on resume require `state_repo == ctx.repo` (or safe-refuse) before any GitHub call.
  - From cursor-specialist-security-output.txt: validate `state_repo` against the same format constraints as `ctx.repo` (e.g., `^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$`) before using it as a `gh` CLI argument.


### FINDING_18: State extra fields and conflict handoff values are insufficiently constrained
- **Reviewer(s)**: dyn-state-io-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `_write_ship_state()` can round-trip or merge unallowlisted state keys and writes `CONFLICT_FILES` values with only newline checks, leaving room for state-key override or shell-sourced assignment injection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-io-output.txt: Allowlist `RESUME_PHASE`/`CALLER_KIND` on read (clear or refuse unknown values), validate `CONFLICT_FILES` as a comma-separated list of repo-relative paths without `..`, newlines, or commas in individual entries before write, and drop `extra_fields` on routine rewrites unless explicitly preserving a known handoff.
  - From cursor-specialist-security-output.txt: add an explicit allowlist check — e.g., `ALLOWED_EXTRA_FIELDS = {"CONFLICT_FILES"}`, raising `ShipError` if a caller supplies a key outside it.
  - From cursor-specialist-security-output.txt: shell-quote the `CONFLICT_FILES` value (e.g., wrap in single quotes, escaping internal single quotes) or validate that `conflict_csv` contains no characters outside `[A-Za-z0-9._/,-]` before writing.


### FINDING_2: Open-pr OOS gates overwrite restored counters with zeroes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-resume-state-output.txt, dyn-github-pr-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: On `open-pr` resume with `OOS_PENDING=true`, `_pending_oos_gate` / `_oos_gate` write `ship-pr-state.sh` with default-zero counters, wiping restored `ITERATION`, `REBASE_COUNT`, `FIX_ATTEMPTS`, and `TRANSIENT_RETRIES`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Thread counters through _oos_gate writes or skip OOS helpers on open-pr without rewriting counter fields
  - From dyn-resume-state-output.txt: Thread the active counter tuple into `_pending_oos_gate` / `_oos_gate` (or read it from the just-written plan) and pass it through every `_write_ship_state` call on those paths; add a test that seeds non-zero counters plus `OOS_PENDING=true` and asserts they survive the refusal.
  - From dyn-github-pr-output.txt: Thread the active counter tuple into `_pending_oos_gate` / `_oos_gate` (or have `_write_ship_state` read-and-preserve existing counter keys when callers omit them on non-`fresh` paths), and extend the open-pr + `OOS_PENDING` test to assert counters survive the gate write.
  - From cursor-specialist-edge-cases-output.txt: Thread `iteration`, `rebase_count`, `fix_attempts`, `transient_retries` as parameters through `_pending_oos_gate` and `_oos_gate`, and pass them to all `_write_ship_state` calls within those functions; the call site in `run_ship` already has `resume.iteration` etc. in scope.


### FINDING_22: Invalid FORKED_TARGET falls back to the wrong ctx field
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `FORKED_TARGET` is present but invalid, `read_durable_flags()` can derive `forked` from `ctx.forked_target` instead of `ctx.forked`, corrupting fork/gh-skip behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Change line 146 to `forked = forked_target if raw_forked_target.strip() in ("true", "false") else ctx.forked` so invalid values fall back to `ctx.forked`.
  - From cursor-specialist-security-output.txt: `forked = forked_target if raw_forked_target.strip() in {"true", "false"} else ctx.forked`.
  - From cursor-specialist-edge-cases-output.txt: `forked = forked_target if raw_forked_target.strip() in {"true", "false"} else ctx.forked`


### FINDING_25: `_state_file_under_tmpdir` accepts the tmpdir directory itself
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `_state_file_under_tmpdir()` returns true when the state path equals the tmpdir, even though a directory cannot be a valid state file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: change the condition to `tmpdir in state_path.parents` (drop the `state_path == tmpdir` case).

### FINDING_4: Plan acceptance and resume matrix coverage is incomplete
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Dedicated tests are missing for multiple plan-required scenarios, including resume routing, cap semantics, blocked rebase continuation, GitHub head verification, repo-unavailable blank PR identity, main/master refusal, Part B Phase 7 coverage, and postmerge non-OK handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add targeted tests for ITERATION 49/50 ci_not_ready cap open-pr OOS counter preservation and GitHub-authoritative stale-state cases
  - From cursor-specialist-testing-output.txt: Add parametrized tests for each plan bullet or unit-test _resume_plan directly.
  - From cursor-specialist-testing-output.txt: Assert two run_ship calls: NEEDS_USER_INPUT twice, state byte-identical on markers/counters.
  - From cursor-specialist-testing-output.txt: Add resume-state tests with stub monitor actions merge/already_merged/wait.
  - From cursor-specialist-testing-output.txt: Add Part B tests or update acceptance criteria.
  - From cursor-specialist-testing-output.txt: Extract/table-test classification matrix with stub runner.
  - From cursor-specialist-plan-fidelity-output.txt: Add two tests: one asserting `needs_user_reason == "unsupported-rebase-continuation"` and that the state file is unchanged, and a second that invokes `run_ship` twice with the same state and asserts the same outcome both times.
  - From cursor-specialist-plan-fidelity-output.txt: Add three `test_cap_*` tests that stub `ci_monitor.monitor` to return the appropriate action and assert STALLED vs OK respectively.
  - From cursor-specialist-plan-fidelity-output.txt: Add a test with `PR_NUMBER=\nREPO_UNAVAILABLE=true` in state, `merge=false`, and assert `result.outcome is Outcome.OK` with checks/postbump forbidden.
  - From cursor-specialist-plan-fidelity-output.txt: Add tests that stub `gh.pr_view` to return `OPEN`/`MERGED` with `head_ref="wrong-branch"` and assert `checks.run_checks_phase` is called (fresh) and postmerge is never called.
  - From cursor-specialist-plan-fidelity-output.txt: Add a test with `BRANCH_NAME=main`, `current_branch=main`, `FORKED_TARGET=false` in state, and assert `needs_user_reason == "checkout-mismatch"` with checks forbidden.
  - From cursor-specialist-plan-fidelity-output.txt: Add a test for the CI-loop success path with `merge.merge_pr` returning a `POST_MERGE_MERGE_RESULTS` result and `finalize.postmerge` returning STALLED, asserting `PHASE=postmerge` in the state and outcome is STALLED.


### FINDING_5: Resume-phase marker is compared with a hardcoded literal
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_resume_plan()` compares against `"ship-pr-rrr-phase14"` directly instead of using `config.SHIP_PR_RRR_RESUME_PHASE`, so future constant changes could break blocked-rebase routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use config.SHIP_PR_RRR_RESUME_PHASE in _resume_plan
  - From cursor-specialist-structure-output.txt: Replace the literal with `config.SHIP_PR_RRR_RESUME_PHASE`.


