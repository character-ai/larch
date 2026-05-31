### FINDING_1: run_waterfall ignores TierAttempt.failure; log KV short-circuit gap
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `run_waterfall` short-circuits only from `LAUNCHER_FAILURE_CLASS=` lines in `failure_log` (via `parse_launcher_failure_class`) and ignores `TierAttempt.failure`. `launch_fn` can set `failure_class` (e.g. `other` via `classify_launch_failure`) without emitting matching log KVs, so the waterfall does not perform first-fixer-non-health bail and may cascade through later tiers (e.g. defaulting to health). Related API drift: planned injectable `classify_fn` is not implemented; integrators may expect classification without capture logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: gh read helpers raise ShipError; plan expects retriable last result
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Read helpers raise `ShipError` after transient retries via `_ensure_success`. Phase 7 orchestration cannot map exhausted transient `gh` reads to `Outcome.TRANSIENT` without catching `ShipError`. Plan text expects retried read exhaustion to return the last `CommandResult` / `StepResult` rather than raising.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Unused `json` import in git.py
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Unused `json` import; dead import may fail future unused-import lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: `WATERFALL_MAX_TIERS` unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `WATERFALL_MAX_TIERS` is defined but unused; constant documents intent but nothing enforces a tier cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Duplicate `_ensure_success` in git.py and gh.py
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicate `_ensure_success` implementations in `git.py` and `gh.py`; error messaging may diverge over time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: `run_list` silently skips malformed JSON rows
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `run_list` skips malformed / non-dict JSON array elements without error. Partial or changed `gh` JSON yields an incomplete run list; orchestrator may misread CI state, skip reruns, or target the wrong workflow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Launcher argv uses relative `scripts/` paths without cwd contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Launch argv uses relative `scripts/` paths without a documented cwd contract; if cwd is not repo root, `launch_tier` may miss scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### OOS_1: [OUT_OF_SCOPE] Stale ignore-patterns in python/.pylintrc
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Stale `ignore-patterns` from copied config; contributor confusion only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: `pr_create` omits `--base` and `--assignee @me`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `pr_create` omits `--base` and `--assignee @me` present in `create-pr.sh`. Future cutover may open PRs against repo default instead of ship-pr-resolved `BASE_REF`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: `failed_jobs` silently skips malformed job dicts
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `failed_jobs` skips malformed job dicts without error; missing job names drop from the failed set and local replay may omit a failing job.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Plan says ship-pr untouched; branch adds python per-job replay
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan acceptance claims `ship-pr.sh` untouched, but the branch adds `python-lint` / `python-tests` to `_per_job_argv` per-job replay. Strangler-fig / acceptance may reject the PR; allowlist-only `ci-failed-jobs` can still yield `ci-local-unfixable` exit 3 without replay mapping. Docs/plan drift from the actual diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] relevant-checks skips py-test/py-lint when tools absent (optional extension)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Optional `py-test` / `py-lint` in `relevant-checks` when dev tools are not on PATH; local passes may not reflect CI. Extends beyond four enumerated non-python Phase 1 edits; extra local validation path not required by Phase 1 acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] gitleaks allowlist for python fixtures and caches
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Gitleaks path allowlist expanded for `python/test_redact.py`, caches, and related paths; synthetic or accidental secrets under allowlisted paths may skip gitleaks layers 1–2 in CI. Supporting `SECURITY.md` / plan file-list drift for Phase 1 enumeration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: Missing transient-retry tests for run_list, run_view, failed_jobs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Idempotent `gh` retry behavior is only tested for `pr_view` and `pr_for_branch`, not `run_list` / `run_view` / `failed_jobs`. A transient failure on run list/view during a future Phase 2+ ship-pr port could fail to retry while PR reads do, diverging from bash retry semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub-runner transient retry and exhaustion tests for run_list, run_view, and failed_jobs matching the pr_view patterns.

### FINDING_12: relevant-checks skips Python targets when tools missing but exits 0
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `relevant-checks` skips `py-test` / `py-lint` when dev tools are absent and still exits 0. `/implement` can report green relevant-checks on `python/**` edits while CI `python-tests` / `python-lint` fail on the same commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document required local installs; consider failing closed when python/*.py changes and pytest is missing, or gate on CI-only for Phase 1.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: test-relevant-checks lacks positive case with Python tools on PATH
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Harness lacks a positive case with all Python tools on PATH. Regression that never appends `py-lint` when tools exist would pass `test-relevant-checks` and only fail in manual/CI runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add Section 3n with stub ruff/pylint/pyright/pytest on PATH asserting both targets run.

### FINDING_14: Timeout test does not assert partial capture
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Timeout test does not assert partial capture. Partial `gh`/`git` output might be dropped on timeout without failing tests, violating the documented proc contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert non-empty stdout/stderr on a timeout result from a child that emits before blocking.

### FINDING_15: No unit test for `with_transient_retry` predicate branch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No unit test for `with_transient_retry` `predicate=` branch. Custom predicate retries (used by bash envelope paths) could regress silently in later phases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one predicate-driven retry test with a fake sleeper.

### FINDING_16: python/README.md outside relevant-checks routing glob
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `python/README.md` and `python/.gitignore` are outside the Python routing glob. README-only security/doc edits to `python/` skip pytest in relevant-checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend routing patterns or document CI-only coverage for doc-only python changes.

### FINDING_17: exit 0 classification lacks bash parity test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: exit 0 classification lacks bash parity test present in `test-lib-external-launcher-common.sh`. Subtle drift on success classification might not be caught until cross-language CI parity runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test_parity_classify_success mirroring the bash harness argv.

### OOS_4: [OUT_OF_SCOPE] make lint omits py-lint/py-test by design
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `make lint` omits `py-lint` / `py-test` by design. Developers who only run `make lint` never exercise the new Python tree locally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_18: PR/issue titles passed to gh without redact
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `pr_create` and `issue_edit` pass title to `gh` without `redact.redact()`. After Phase 7 cutover, a PR or issue title containing a GitHub PAT or tmpdir path may be published to GitHub in cleartext.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: Breadcrumbs and JSONL journal write unredacted caller text
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Breadcrumbs and `JsonlJournal` write unredacted caller text / arbitrary fields. Future wiring may log raw `gh` stderr or secrets to disk under `IMPLEMENT_TMPDIR` without a enforced redaction boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: No fail-closed redact_gh_error; raw gh stderr retained
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: No `redact_gh_error` fail-closed helper; `CommandResult` retains raw `gh` stderr. Operator-facing logs or issue comments may include token-bearing 4xx bodies from `gh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_21: `ls_files` omits `--` before path operands
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ls_files` omits `--` before path operands. Untrusted paths such as `-u` or `--debug` may be parsed as git flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] Bash create-pr sends unredacted title (pre-existing)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Bash `create-pr` sends unredacted title to `gh` (pre-existing). Same title leakage class as new `gh.py` for PR titles only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_22: `rev_count` bare `int()` may raise ValueError instead of ShipError
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `rev_count` uses bare `int()` without `ShipError` wrapper. Unexpected git stdout raises `ValueError` instead of `ShipError`, breaking uniform recovery in later orchestration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: `first_tier` ignored for rotation when not in tiers list
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `first_tier` is ignored for rotation when not in the tiers list; short-circuit is keyed off `tier_list[0]` not the requested offset, diverging from bash `start_attempt % 3` semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_24: subprocess `text=True` lacks `errors=replace`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `text=True` subprocess capture in `proc.py` lacks `errors=replace`. Binary or invalid UTF-8 child output may crash `proc.run` instead of returning `CommandResult`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Full CI-fix waterfall in ship-pr not ported to Python agents
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Full CI-fix waterfall includes rollback/verify/bail not ported to Python. Phase 7 must not assume `agents.run_waterfall` equals `run_ci_fix_vendor`; keep orchestration in ship-pr until explicitly migrated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_25: `build_launch_argv` targets bash launch scripts, not agent CLIs
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `build_launch_argv` targets `scripts/launch-*-ci.sh` instead of cursor/codex/claude CLIs per plan and locked architecture. Phase 7 cutover inherits a bash-wrapper seam contrary to true-externals-only subprocess policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_26: CI uses Makefile py targets vs plan direct python invocations
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: CI runs `make py-lint` / `make py-test` instead of plan's `working-directory: python` direct linter invocations. Low risk of Makefile/workflow drift if targets change independently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] Plan understates ship-pr _per_job_argv for fixable jobs
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan failure-mode text understates need for ship-pr `_per_job_argv` when jobs are fixable. Fixable classification without argv mapping still exits 3; ship-pr edit closes a gap the plan did not fully specify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
