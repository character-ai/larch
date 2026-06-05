### FINDING_1: Merge-retry continuations can bypass the iteration cap
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The merge-retry path can loop past the session iteration cap because cap enforcement moved into the non-merge branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reapply cap at loop entry for merge-retry continuations or check cap immediately after ci_not_ready/main_advanced increment

### FINDING_2: Open-pr OOS gates overwrite restored counters with zeroes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-resume-state-output.txt, dyn-github-pr-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: On `open-pr` resume with `OOS_PENDING=true`, `_pending_oos_gate` / `_oos_gate` write `ship-pr-state.sh` with default-zero counters, wiping restored `ITERATION`, `REBASE_COUNT`, `FIX_ATTEMPTS`, and `TRANSIENT_RETRIES`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Thread counters through _oos_gate writes or skip OOS helpers on open-pr without rewriting counter fields
  - From dyn-resume-state-output.txt: Thread the active counter tuple into `_pending_oos_gate` / `_oos_gate` (or read it from the just-written plan) and pass it through every `_write_ship_state` call on those paths; add a test that seeds non-zero counters plus `OOS_PENDING=true` and asserts they survive the refusal.
  - From dyn-github-pr-output.txt: Thread the active counter tuple into `_pending_oos_gate` / `_oos_gate` (or have `_write_ship_state` read-and-preserve existing counter keys when callers omit them on non-`fresh` paths), and extend the open-pr + `OOS_PENDING` test to assert counters survive the gate write.
  - From cursor-specialist-edge-cases-output.txt: Thread `iteration`, `rebase_count`, `fix_attempts`, `transient_retries` as parameters through `_pending_oos_gate` and `_oos_gate`, and pass them to all `_write_ship_state` calls within those functions; the call site in `run_ship` already has `resume.iteration` etc. in scope.

### FINDING_3: [OUT_OF_SCOPE] Manifest DONE status is implemented but not consumed by resume routing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-resume-state-output.txt, dyn-github-pr-output.txt, dyn-ci-caps-output.txt, dyn-postmerge-flow-output.txt
- **Severity**: important
- **Concern**: `run_logs.manifest_status()` exists, but `_resume_plan()` does not use it, leaving gh-skipped merged/done routing under-wired relative to the plan’s qualified manifest predicates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fold manifest_status into local_merged only when another merged predicate already agrees
  - From cursor-specialist-testing-output.txt: Wire per plan with guards or add test documenting manifest ignored for merged.

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

### FINDING_6: [OUT_OF_SCOPE] Terminal state PHASE loses the specific stall step
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Terminal stall state writes a coarse `PHASE=stalled` instead of preserving the specific step token, reducing operator visibility into stall cause.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Consider preserving step in PHASE or document Python-only coarser PHASE contract

### FINDING_7: [OUT_OF_SCOPE] Fresh fallback can persist stale counters
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-ci-caps-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Fresh resume paths can carry restored non-zero counters into state writes even though CI locals start at zero, causing inconsistent cap accounting across handbacks or later open-pr resumes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Force zero counters in `_fresh_resume_plan()` (or zero them at the start of the `fresh` branch) for all state writes on that path; keep counter restoration exclusively for validated `open-pr` / `merged` / terminal handback paths.
  - From dyn-ci-caps-output.txt: When `resume.start == "fresh"`, pass zeros into all `_write_ship_state` / `_write_terminal_state` calls (or build `_fresh_resume_plan` without forwarding read counters except on explicit `open-pr` / `merged` / `done` resumes). Align `test_fresh_fallback_hydrates_modes_and_preserves_counters` with that contract if stale-counter preservation on gh-failure fresh was not intentional.
  - From cursor-specialist-plan-fidelity-output.txt: Consider zeroing counters in the state write for the fresh path (not the open-pr seed, which already uses 0) so stale restored values cannot bleed into the next open-pr CI start

### FINDING_8: Resume can proceed without a durable persisted branch anchor
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: important
- **Concern**: For normal repos, resume validation can fall back to argv/env branch values when persisted `BRANCH_NAME` is empty, weakening the durable branch validation guarantee.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: After `blocked-rebase-continuation`, require a non-empty persisted `BRANCH_NAME` for any non-`fresh` resume (not only `gh_skipped`), and safe-refuse when it is missing or does not equal the probed current branch; do not fall back to `ctx.branch` for anchor validation once a state file exists.

### FINDING_9: [OUT_OF_SCOPE] Additional plan-listed test gaps remain unpinned
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-github-pr-output.txt, dyn-ci-caps-output.txt, dyn-postmerge-flow-output.txt
- **Severity**: important
- **Concern**: Out-of-scope reviewer notes identify additional missing regression coverage for acceptance-matrix cases such as wrong PR head, repeated blocked-rebase continuation, cap 49/50, terminal handback round trips, gh/fork/repo-unavailable routing, and main CI postmerge non-OK behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt, dyn-github-pr-output.txt, dyn-ci-caps-output.txt, dyn-postmerge-flow-output.txt: Address the concern above.

### FINDING_10: GitHub PR lookup failures are degraded to fresh reruns
- **Reviewer(s)**: dyn-github-pr-output.txt
- **Severity**: important
- **Concern**: `_resume_plan()` treats transient and non-transient `gh.pr_view` failures as `fresh`, which can rerun checks/postbump, reset CI budgets, or churn an already-open PR instead of preserving resume metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-github-pr-output.txt: Distinguish `TransientNetworkError` (return `Outcome.TRANSIENT` without a full fresh pipeline) from permanent lookup failures; when state + branch are valid but `gh` is temporarily unreachable, prefer `open-pr` resume using persisted identity or a safe-refuse that preserves counters rather than `fresh` with zero-seeded CI locals.
  - From dyn-github-pr-output.txt: Catch `TransientNetworkError` separately for the handback above; map other `ShipError`/`ShipError`-family read failures to `NEEDS_USER_INPUT` or `STALLED` with explicit detail, leaving counters and `RESUME_PHASE` intact.

### FINDING_11: Fresh fallback can retain stale PR identity in context/state
- **Reviewer(s)**: dyn-github-pr-output.txt
- **Severity**: important
- **Concern**: `_hydrate_fresh_context()` leaves `ctx.pr_number` / `ctx.pr_url` intact after `_resume_plan()` degrades to fresh, creating a window where persisted state disagrees with GitHub ground truth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-github-pr-output.txt: Clear `pr_number`/`pr_url` (and optionally `merge_result`/`pr_closed`) in `_hydrate_fresh_context`, or hydrate them from the `ResumePlan` (`pr_number=None`, `pr_url=""`) whenever `start == "fresh"`.

### FINDING_12: [OUT_OF_SCOPE] Open-pr resume can bypass leftover security/OOS sidecar material
- **Reviewer(s)**: dyn-github-pr-output.txt
- **Severity**: latent
- **Concern**: Open-pr resume skips `_materialize_manifest_oos` and the security sidecar unless `OOS_PENDING` is set, so leftover OOS/security observations from an interrupted fresh run may be bypassed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-github-pr-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Terminal CI handbacks may not persist consumed fixing attempts
- **Reviewer(s)**: dyn-ci-caps-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `_monitor_persisted_counters()` increments `transient_retries` but not `fix_attempts` for terminal handbacks with `monitor.did_fixing=True`, diverging from the plan language and potentially allowing an extra fixing attempt after resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-caps-output.txt: If parity with bash is intended, document the asymmetry in `_monitor_persisted_counters` and keep tests; if the plan’s “consumed increments” language means all `did_fixing` cycles, increment `fix_attempts` (and persist `rebase_count` when `goto_rebase` completed) in `_monitor_persisted_counters` before `_write_terminal_state`, and extend tests beyond the current failed-fixing case.
  - From cursor-specialist-security-output.txt: Resolve plan-vs-test contradiction; if test is authoritative, update plan description to say terminal handbacks do not count failed fix attempts
  - From cursor-specialist-edge-cases-output.txt: Add `fix_attempts=fix_attempts + (1 if monitor.did_fixing else 0)` as the third tuple element, or document in the helper that terminal handbacks intentionally do not count `did_fixing` and update the plan spec to match.
  - From cursor-specialist-plan-fidelity-output.txt: Either document this deliberate divergence in the plan/code comment and update the acceptance criterion, or increment `fix_attempts` in `_monitor_persisted_counters` (matching `iteration` + `transient_rerun_attempted`) so the terminal and continue paths agree.

### FINDING_14: Legacy PHASE=done can skip required postmerge recovery
- **Reviewer(s)**: dyn-postmerge-flow-output.txt
- **Severity**: important
- **Concern**: Normal-repo resume treats `PHASE=done` plus GitHub `MERGED` as terminal success, but legacy state may have written `PHASE=done` even when postmerge did not complete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-postmerge-flow-output.txt: When GitHub reports `MERGED`, only classify `start="done"` if postmerge completion is corroborated (for example `run_logs.manifest_status(ctx) == config.MANIFEST_STATUS_DONE`, and/or `post-merge-sentinel` plus a non-stalled finalize snapshot); otherwise keep routing to `merged` so postmerge is retried even when stale local `PHASE=done` is present.

### FINDING_15: [OUT_OF_SCOPE] finalize.postmerge OK can still mask partial cleanup
- **Reviewer(s)**: dyn-postmerge-flow-output.txt
- **Severity**: latent
- **Concern**: Pre-existing behavior allows `finalize.postmerge()` to return `Outcome.OK` despite unexpected main status or partial cleanup, after which the driver writes `PHASE=done`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-postmerge-flow-output.txt: Address the concern above.

### FINDING_16: State durable flags can force gh-skipped resume behavior
- **Reviewer(s)**: dyn-state-io-output.txt
- **Severity**: important
- **Concern**: Resume treats durable flags from `ship-pr-state.sh` as authoritative without cross-checking the invoking session, so tampered state can set `REPO_UNAVAILABLE=true` or `FORKED_TARGET=true` and bypass GitHub-authoritative checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-io-output.txt: Treat state durable flags as a cache, not sole truth: on non-fresh resume, require agreement with argv/`session-env.sh` (or a signed bootstrap nonce), or refuse resume when `ctx.forked_target`/`ctx.repo_unavailable` disagree with hydrated state unless `repo_unavailable` was explicitly established at session start.

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

### FINDING_19: Open-pr branch redundantly rereads OOS_PENDING
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The open-pr branch reads `OOS_PENDING` from state even though `_hydrate_resume_context()` already populated `pr_context.oos_pending`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Simplify to `elif pr_context.oos_pending:`.

### FINDING_20: Dead `_ = step` assignment is misleading
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_ = step` adds no semantics because `step` is already used as `stall_step=step`, and it misleadingly suggests the value is discarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove `_ = step`.

### FINDING_21: `_write_ship_state` repeatedly rereads resume metadata
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_write_ship_state()` reads `RESUME_PHASE` and `CALLER_KIND` from disk on common-path writes, adding repeated file reads through the CI loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Read `RESUME_PHASE`/`CALLER_KIND` once in `_resume_plan` or at the top of `run_ship()`, store them on the context or pass them through, and remove the in-place reads from `_write_ship_state`.

### FINDING_22: Invalid FORKED_TARGET falls back to the wrong ctx field
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `FORKED_TARGET` is present but invalid, `read_durable_flags()` can derive `forked` from `ctx.forked_target` instead of `ctx.forked`, corrupting fork/gh-skip behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Change line 146 to `forked = forked_target if raw_forked_target.strip() in ("true", "false") else ctx.forked` so invalid values fall back to `ctx.forked`.
  - From cursor-specialist-security-output.txt: `forked = forked_target if raw_forked_target.strip() in {"true", "false"} else ctx.forked`.
  - From cursor-specialist-edge-cases-output.txt: `forked = forked_target if raw_forked_target.strip() in {"true", "false"} else ctx.forked`

### FINDING_23: State boolean parsing is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `ship.py` duplicates the boolean parsing already implemented in `run_logs._state_bool_or_default()`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Export `state_bool_or_default` from `run_logs` and call it from `ship.py` instead of the local copy.

### FINDING_24: Open-pr-only branch is hidden behind a bare else
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: A bare `else` hides that the branch is only reachable for `resume.start == "open-pr"`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Replace `else:` with `elif resume.start == "open-pr":` (and optionally add a final `else: raise AssertionError(resume.start)` for safety).

### FINDING_25: `_state_file_under_tmpdir` accepts the tmpdir directory itself
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `_state_file_under_tmpdir()` returns true when the state path equals the tmpdir, even though a directory cannot be a valid state file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: change the condition to `tmpdir in state_path.parents` (drop the `state_path == tmpdir` case).
