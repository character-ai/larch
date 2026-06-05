### FINDING_1: [OUT_OF_SCOPE] Post-monitor iteration cap check is unreachable / does not enforce the intended at-cap stall
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-resume-state-output.txt, dyn-github-pr-output.txt, dyn-counter-limits-output.txt, dyn-postmerge-idem-output.txt, dyn-oos-skip-output.txt
- **Severity**: important
- **Concern**: The inner `iteration > SHIP_MERGE_LOOP_MAX_ITERATIONS` check inside the non-merge monitor branch uses the same unmodified `iteration` value as the top-of-loop guard, making that branch unreachable. Reviewers disagreed whether the intended fix is removal or changing the post-monitor guard to enforce an immediate at-cap stall, but all describe the same cap-enforcement ambiguity/dead-code risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove the inner `if iteration > config.SHIP_MERGE_LOOP_MAX_ITERATIONS:` block (lines 1345–1360) entirely; the outer check already provides the required cap-before-monitor semantics.
  - From cursor-specialist-correctness-output.txt: change line 1273 to `if iteration >= config.SHIP_MERGE_LOOP_MAX_ITERATIONS:` so the post-decision cap fires at exactly `MAX`.
  - From cursor-specialist-edge-cases-output.txt: Remove the inner cap check block entirely (diff lines 1345–1360); the top-of-loop Check A enforces the cap correctly on the subsequent iteration.
  - From dyn-resume-state-output.txt: Remove the post-monitor cap block at lines 1273-1288 entirely; the pre-monitor check at line 1211 already handles all cases. If the intent is to let monitor run at exactly `cap` and stall in the same iteration on non-pass/non-merged outcome, move the ENTIRE cap check to after the monitor call inside the `if monitor.action not in {"merge", "already_merged"}:` block using `iteration` AFTER the increment (`iteration + 1 > cap` at the top of the block, before `_write_ship_state`), and delete the pre-monitor check.
  - From dyn-github-pr-output.txt: Remove the duplicate inner `if iteration > config.SHIP_MERGE_LOOP_MAX_ITERATIONS` block at lines 1273–1288; the outer pre-loop guard already enforces the cap correctly (changed from `>=` to `>` to allow one final monitor cycle at the cap).
  - From dyn-counter-limits-output.txt: Change the post-monitor guard to `if iteration >= config.SHIP_MERGE_LOOP_MAX_ITERATIONS` while leaving the top-of-loop guard as `>`.
  - From dyn-postmerge-idem-output.txt: Remove the duplicate cap block at lines 1273-1288 entirely; the sole enforcement point should remain at line 1211 where `iteration > MAX` is checked before every monitor call.
  - From dyn-oos-skip-output.txt: Remove the inner `if iteration > config.SHIP_MERGE_LOOP_MAX_ITERATIONS:` block inside the non-merge action branch; the outer check at the top of the loop already provides the correct cap semantics.

### FINDING_2: Open-pr resume still runs OOS gates despite plan saying to skip them
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-pr-output.txt, dyn-postmerge-idem-output.txt, dyn-oos-skip-output.txt
- **Severity**: important
- **Concern**: The `open-pr` resume path calls `_pending_oos_gate`, which includes the security OOS file gate and `_oos_gate`, contradicting the plan’s stated skip-all-OOS-helper behavior for open-pr resumes. This can re-block an otherwise valid resume on stale or changed OOS artifacts, and several tests appear to encode the plan-divergent behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove the `elif resume.start == "open-pr":` OOS gate block entirely; the counter-safe OOS path was already addressed by threading counters through `_pending_oos_gate` — but per plan the entire gate should be skipped on open-pr resume.
  - From cursor-specialist-correctness-output.txt: guard the OOS gate block with `if resume.start == "fresh":` only, aligning with the plan; if the intent is to preserve OOS re-evaluation on resume, document that this is an intentional divergence and update the plan tests accordingly.
  - From cursor-specialist-testing-output.txt: Either remove `_pending_oos_gate` from the open-pr path (matching plan) or explicitly document the deviation and add a comment explaining why OOS is re-checked on open-pr resume.
  - From cursor-specialist-security-output.txt: Add a comment at the open-pr OOS gate call explaining that this is a deliberate divergence from the skip-all spec, or align the test name/assertions with the actual intent.
  - From cursor-specialist-edge-cases-output.txt: Either remove `_pending_oos_gate` from the `open-pr` branch (matching the plan's skip intent) and document why it's safe to skip, or explicitly update the plan to reflect that OOS re-checking on resume is desired and document the scenarios where it triggers.
  - From cursor-specialist-plan-fidelity-output.txt: Move `_pending_oos_gate` out of the `elif resume.start == "open-pr"` branch; for open-pr resume, skip directly to `ensure_pr`. Replace `test_open_pr_resume_preserves_pending_oos_gate` with a test that marks the gate as `forbidden` on open-pr.
  - From dyn-resume-state-output.txt: Remove the `elif resume.start == "open-pr": oos_result = _pending_oos_gate(...)` block (lines 1154-1165).
  - From dyn-github-pr-output.txt: Move the `_pending_oos_gate` call for `open-pr` behind a guard that returns early without calling the gate (matching the `_materialize_manifest_oos` guard that is correctly skipped), so the open-pr path proceeds directly from `_write_ship_state(phase="pr-create")` to `_pr_title`/`ensure_pr` without re-entering OOS checks.
  - From dyn-postmerge-idem-output.txt: Align either the plan acceptance criteria or the test to be explicit about this behavior. If the OOS gate should run on open-pr to catch pending artifacts, update the plan wording; if it should be skipped, guard the `_pending_oos_gate` call at line 1154 behind `resume.start == "fresh"` only (matching the `_materialize_manifest_oos` guard already in place).
  - From dyn-oos-skip-output.txt: Remove the `elif resume.start == "open-pr":` block that calls `_pending_oos_gate`—open-pr resumes already passed the OOS gate before the PR was created and should proceed directly to `ensure_pr`.

### FINDING_3: [OUT_OF_SCOPE] `manifest_status` uses `ctx.run_id` instead of `effective_run_id(ctx)`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-github-pr-output.txt, dyn-postmerge-idem-output.txt
- **Severity**: latent
- **Concern**: `manifest_status` reads the manifest under `ctx.run_id` rather than the effective run id used by `_manifest_path`, so it can miss the actual manifest when state-file `RUN_ID` and context `run_id` diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Replace `ctx.run_id` on line 147 with `effective_run_id(ctx)` (the function is already in the same module), and update the test name/assertion to match.
  - From cursor-specialist-correctness-output.txt: use `effective_run_id(ctx)` consistent with `_manifest_path`.
  - From cursor-specialist-edge-cases-output.txt: Either document this divergence from `effective_run_id` in the function docstring and ensure all callers have already hydrated `ctx.run_id` from state before calling, or align with `effective_run_id` as the plan states and update the test to match.
  - From cursor-specialist-plan-fidelity-output.txt: Use `effective_run_id(ctx)` in the path construction to match the `_manifest_path` contract, or update the plan/docstring to explicitly document why `ctx.run_id` is preferred.

### FINDING_4: [OUT_OF_SCOPE] `_fresh_resume_plan` accepts counters but always discards them
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt
- **Severity**: nit
- **Concern**: `_fresh_resume_plan` exposes a `counters` parameter even though fresh plans always seed counters to zero. Passing restored counters at call sites is therefore silently ignored and misleading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove the `counters` parameter from `_fresh_resume_plan`'s signature and all call sites; always construct zeros inline.
  - From cursor-specialist-testing-output.txt: Remove the `counters` parameter entirely since `fresh` always zeros counters per spec.
  - From cursor-specialist-edge-cases-output.txt: Remove the `counters` parameter entirely and remove the `counters=counters` kwargs at all call sites; document the zero-seed invariant clearly in the function signature.
  - From cursor-specialist-plan-fidelity-output.txt: Remove the `counters` parameter from `_fresh_resume_plan` since it is never used; update call sites to omit it.
  - From dyn-resume-state-output.txt: Remove the `counters` parameter from `_fresh_resume_plan` entirely.

### FINDING_5: `_write_terminal_state` has a misleading `_ = step` after `step` is already used
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `_ = step` appears after `step` is passed to `finalize.write_finalize_state`, so the unused-variable idiom is unnecessary and misleading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove `_ = step`; the parameter is used above it and pyright should not warn about a parameter that appears in a function call.
  - From cursor-specialist-edge-cases-output.txt: Remove the `_ = step` line.

### FINDING_6: Duplicate boolean parsing helpers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_state_bool_text(value)` duplicates the behavior of `run_logs._state_bool_or_default(value, default=False)`, creating two private implementations of the same parsing rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Either make `_state_bool_or_default` a public helper in `run_logs` (rename to `parse_state_bool`) and reuse it, or add a thin public wrapper — eliminating the duplication.

### FINDING_7: [OUT_OF_SCOPE] State validation failures are reported as checkout mismatches
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Non-checkout state validation failures route through checkout-mismatch naming/reasoning, which can mislead users into debugging their git checkout instead of malformed or mismatched state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Introduce a separate `blocked-state-invalid` start value (or at minimum a separate `needs_user_reason` string like `"state-invalid"`) for non-branch validation failures, keeping `"checkout-mismatch"` only for genuine branch/HEAD mismatches and the main/master guard.

### FINDING_8: `manifest_status` is defined/tested but not wired into `_resume_plan`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `manifest_status(ctx)` is not used in `ship.py` resume classification, so manifest `DONE` is absent from the gh-skipped merged-routing predicate despite the plan describing it as a signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: add `or (run_logs.manifest_status(ctx) == "DONE" and <at least one other predicate>)` to `local_merged`.
  - From cursor-specialist-testing-output.txt: Either call `manifest_status(ctx)` in the `local_merged` calculation (with the agreement guard the plan describes) or remove the function and its tests if it's intentionally out-of-scope.
  - From cursor-specialist-security-output.txt: Either wire it into the gh-skipped merged detection, or remove it until it's needed.

### FINDING_9: Plan-required test scenarios are missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Multiple plan-required scenarios are not covered by tests, including wrong-PR-head fresh routing, non-forked main/master refusal, closed-unmerged PR routing, repo-unavailable blank-PR open-pr resume, iteration-cap non-pass behavior, main CI postmerge non-OK phase handling, detached HEAD refusal, and rebase-continuation preservation/idempotency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: add the missing test cases per the plan's test-matrix checklist.
  - From cursor-specialist-testing-output.txt: Add tests that stub `gh.pr_view` returning `head_ref != current_branch` for OPEN, MERGED, and PHASE=done states and assert checks/postbump run (fresh path) and no postmerge is reached.
  - From cursor-specialist-testing-output.txt: Add a test where `state BRANCH_NAME=main`, `current_branch=main`, `FORKED_TARGET=false`, and assert `NEEDS_USER_INPUT` with `needs_user_reason == "checkout-mismatch"`.
  - From cursor-specialist-testing-output.txt: Add a test with `PHASE=postmerge`, stale `MERGE_RESULT`, `gh.pr_view` returning `state="CLOSED"`, and assert checks/postbump run (fresh path).
  - From cursor-specialist-testing-output.txt: Add a test that takes the full fresh→checks→CI→merge→postmerge path with postmerge returning `Outcome.STALLED` and asserts `PHASE=postmerge` (not `PHASE=done`) in state.
  - From cursor-specialist-testing-output.txt: After calling `run_ship`, assert that `state_file.read_text()` still contains `RESUME_PHASE=<value>`, `PHASE=ci-initial`, and `CALLER_KIND` unchanged; then call `run_ship` a second time and assert the same `NEEDS_USER_INPUT` outcome.
  - From cursor-specialist-testing-output.txt: Add a test where `git.current_branch` returns `""` with a state file present and assert `NEEDS_USER_INPUT` / `checkout-mismatch`.
  - From cursor-specialist-testing-output.txt: Add a test with `REPO_UNAVAILABLE=true`, no `PR_NUMBER`/`PR_URL`, valid state branch, and `MERGE=false` asserting `Outcome.OK` without checks/postbump.
  - From cursor-specialist-testing-output.txt: Add a variant with `action="wait"` and assert the result is `Outcome.STALLED` with "merge loop iteration cap reached".
  - From cursor-specialist-edge-cases-output.txt: Add a test that starts from `fresh`, drives through the CI loop to a successful merge, stubs `run_postmerge_phase` to return `STALLED`, and asserts `PHASE=postmerge` (not `PHASE=done`) in the final state file.
  - From cursor-specialist-plan-fidelity-output.txt: Add dedicated tests for the absent scenarios, especially the main/master guard refuse case, wrong-head routing, CLOSED routing, and the two-invocation rebase-continuation preservation test.

### FINDING_10: `PR_URL` validation permits `http://`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `_PR_URL_RE` accepts plaintext `http://` PR URLs, which could propagate insecure URLs to downstream consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restrict the regex to `^https://` only; GitHub.com always uses HTTPS and GitHub Enterprise deployments should redirect.

### FINDING_11: Repo slug validation allows a repo segment starting with `-`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `_valid_repo_slug` rejects slugs starting with `-` but allows the repo-name segment after `/` to start with `-`; reviewers note this is likely not argument injection in the current subprocess shape but remains an incomplete guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Either add an assertion that neither segment starts with `-`, or note this as an accepted gap given the subprocess call is `--repo <value>`.

### FINDING_12: [OUT_OF_SCOPE] Shell-metacharacter validation gaps for state fields such as `PR_TITLE`
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-state-file-output.txt
- **Severity**: latent
- **Concern**: Some fields written to `ship-pr-state.sh`, especially `PR_TITLE`, are only newline-checked and may contain shell metacharacters if any bash consumer sources the state file unsafely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: add allowlist/escape validation for PR_TITLE at the write site, or ensure all bash consumers source with `key="$(grep ...)"` quoting.
  - From dyn-state-file-output.txt: PR_TITLE warrants an explicit allowlist or shell-safe quoting on the write path.

### FINDING_13: Terminal ship-state phase now discards the descriptive `step`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-postmerge-idem-output.txt
- **Severity**: nit
- **Concern**: `_write_terminal_state` writes `PHASE=stalled` for all non-OK terminal states instead of preserving the descriptive step in ship state, which may be intentional but is undocumented and loses diagnostic granularity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Either document this normalization in the plan/changelog, or clarify that the plan authorized it during review rounds.
  - From dyn-postmerge-idem-output.txt: Either explicitly document that `PHASE=stalled` is now canonical for all non-OK terminal states (remove the `step` parameter from the signature to avoid confusion), or restore `phase = "done" if result is Outcome.OK else step or "stalled"` to maintain diagnostic parity with the bash driver.

### FINDING_14: Blocked rebase-continuation path can return unvalidated `PR_URL`
- **Reviewer(s)**: dyn-state-file-output.txt
- **Severity**: important
- **Concern**: `_resume_plan()` can return early for `blocked-rebase-continuation` using `state_pr_url or ctx.pr_url` before later URL validation, allowing invalid schemes to propagate into `ShipResult.pr_url`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-file-output.txt: Move the `_valid_pr_url(state_pr_url)` guard to before the `blocked-rebase-continuation` return, or explicitly clear the URL when it fails: `pr_url = (state_pr_url if _valid_pr_url(state_pr_url) else "") or (ctx.pr_url if _valid_pr_url(ctx.pr_url) else "")`. Similarly add `if not _valid_repo_slug(state_repo): state_repo = ctx.repo` before the blocked-rebase-continuation return.

### FINDING_15: `_monitor_persisted_counters` can overcount rebase attempts on terminal non-OK monitor outcomes
- **Reviewer(s)**: dyn-counter-limits-output.txt
- **Severity**: latent
- **Concern**: `_monitor_persisted_counters` increments `rebase_count` whenever `monitor.goto_rebase` is true, even on terminal non-OK monitor results where no rebase was actually attempted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-counter-limits-output.txt: Only apply the `goto_rebase` increment in `_monitor_persisted_counters` when the monitor result is also OK (i.e., the rebase action was actually issued and the monitor did not terminate). For terminal non-OK outcomes, `goto_rebase` should be treated as inapplicable and `rebase_count` should be left unchanged, mirroring how `iteration` is not incremented on terminal handbacks.

### FINDING_16: [OUT_OF_SCOPE] Merge-retry results can loop without consuming iteration budget
- **Reviewer(s)**: dyn-counter-limits-output.txt
- **Severity**: latent
- **Concern**: Merge retry outcomes such as CI-not-ready/main-advanced continue without incrementing `iteration`, so a permanent retry condition may bypass the iteration cap indefinitely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-counter-limits-output.txt: worth adding a separate `merge_retry_count` cap or a maximum consecutive merge-retry guard.
