### FINDING_1: Plan acceptance vs live ship-pr.sh Python replay wiring
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch adds live `scripts/ship-pr.sh` changes (python-lint/python-tests job argv mapping and local CI replay) while plan/acceptance still claims `ship-pr.sh` is untouched and zero live-path change. Acceptance criteria and the plan should explicitly list `ship-pr.sh` replay wiring, or defer that wiring until the Python cutover phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: ship-pr local Python CI replay without toolchain/deps
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Per-job replay in live `ship-pr.sh` runs `make py-lint` / `make py-test` without ensuring Python requirements or Node tooling are installed. When CI python jobs fail during `/implement`, local replay can fail immediately on missing ruff/pylint/pyright/pytest/node, producing opaque fix-loop behavior instead of a clear recovery path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Install python/requirements-*.txt (and Node) before replay or detect missing tools and skip to vendor fixer with explicit signal
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: effective_failure_class vs bash launcher log semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-waterfall-semantics-output.txt
- **Severity**: important
- **Concern**: `effective_failure_class` does not mirror bash `ship_pr_read_launcher_failure_class` when `failure_log` is set. If the capture file exists but lacks a valid `LAUNCHER_FAILURE_CLASS=` line, bash defaults to `health` and continues the waterfall; Python can fall back to `attempt.failure.failure_class` (e.g. `other`) and short-circuit after one tier. The helper also duplicates `parse_launcher_failure_class` log scanning, so future allowlist edits can diverge. Default to health when the log is missing/invalid; delegate to `parse_launcher_failure_class` when `failure_log` is present; ensure Phase 7 `launch_fn` always passes `failure_log`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-waterfall-semantics-output.txt: When `attempt.failure_log` is set and the path is a file, delegate to `parse_launcher_failure_class(attempt.failure_log)` (same none/health/other + default-health rules as bash); only use `attempt.failure.failure_class` when no log path was supplied. Add a waterfall test with a nonempty capture file lacking `LAUNCHER_FAILURE_CLASS=` and `failure_class="other"` to assert no short-circuit, plus the mirror case with `LAUNCHER_FAILURE_CLASS=other` in the log.

### FINDING_4: build_launch_argv uses repo-relative launcher paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `build_launch_argv` uses repo-relative `scripts/` paths while bash ship-pr uses absolute `$SCRIPT_DIR` launcher paths. With `proc.run` and `cwd` not at the plugin root, launch scripts may not execute even though bash ship-pr works.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_5: JsonlJournal / BreadcrumbWriter emit unredacted text
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: After Phase 7 wires gh/git stderr into journal or breadcrumbs, PATs in tool output could be persisted to tmpdir JSONL or stderr without redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: TransientNetworkError carries raw CommandResult
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `TransientNetworkError` exposes raw `CommandResult` with no `redact_gh_error` port; future callers logging `exc.result.stderr` could leak tokens from gh auth failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_7: git reset/rebase/push flag injection via arbitrary ref strings
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: git helpers accept arbitrary mode/ref strings; user-controlled refs starting with `-` could enable git CLI flag injection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_8: relevant-checks skips Python gates when toolchain absent
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When python tools are missing from PATH, `scripts/relevant-checks.sh` skips `py-lint`/`py-test` with exit 0. `/implement` Step 5 can pass on python-only diffs without running pytest/linters; regressions surface only in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Fail closed when python/*.py changes and toolchain absent, or auto pip install requirements before running make targets
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: relevant-checks always runs full py-lint/py-test on any python/*.py change
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Any change under `python/*.py` triggers full-tree `py-lint` and `py-test`; editing a single test file still lints the entire python tree locally, which may slow iteration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: launch_tier invokes .sh without explicit bash
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Launcher scripts are invoked without a `bash` prefix; if scripts lose `+x` in a consumer checkout, `Popen` fails where explicit `bash` would still work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_11: run_waterfall skips rotation when first_tier absent from tiers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: When `first_tier` is not in `tiers`, rotation is skipped and policy uses the wrong tier vs bash offset semantics. Stale `first_tier` names can short-circuit incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_12: transient retry substring ordering diverges from bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Ordered substring checks for EOF/during, git fetch/failed, lookup/no such host differ from `scripts/lib-net.sh`. Reordered transient stderr may not retry in Python but would in bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_13: failed_jobs silently skips non-dict job rows
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Malformed gh JSON with non-dict job rows is skipped silently, yielding incomplete failed-job lists and wrong CI-fix targeting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: rev_count bare int() on git stdout
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Unexpected git stdout after success raises `ValueError` instead of `ShipError`, which can abort a future Python ship-pr step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: _redact_tmpdir_paths multiline $-anchor parity gap
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `_redact_tmpdir_paths()` applies `$`-anchored operator patterns to the full blob without `re.MULTILINE`, so end-of-line matches on interior lines fail vs bash `sed` line-by-line behavior. Real multiline bodies can leave operator-repo paths unredacted; existing tests use single-line or literal `\n` sequences and miss this.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: compile the tmpdir/operator patterns with `re.MULTILINE` (so `^`/`$` behave like sed’s per-line anchors), or split on `\n` and run the same substitution per line before rejoining; add a bash-parity fixture with actual embedded newlines and an operator-repo root on a non-final line.

### FINDING_16: pr_create TOCTOU recovery missing stderr URL fallback
- **Reviewer(s)**: dyn-gh-retry-policy-output.txt
- **Severity**: important
- **Concern**: After create conflict, `pr_create` only re-queries `pr_for_branch`; if list returns `[]` (index lag) or retries exhaust, Python can fail even when `gh pr create` stderr embeds the existing PR URL. Bash recovers via URL regex; Python cutover could falsely fail PR creation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-retry-policy-output.txt: After `_is_create_conflict`, keep the `pr_for_branch` fast path but add the bash-equivalent fallback: regex-extract `https?://…/pull/\d+` from `_combined(result)`, derive the PR number, and return a `PullRequest` (optionally one non-retried `pr view` if `headRefName` is required); add a `test_gh.py` case mirroring `create_exists_persistent_list`.

### FINDING_17: pr_for_branch open-only can miss closed PRs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Open-only branch lookup can miss closed/merged PRs, causing `pr_create` to retry create/conflict instead of returning the existing PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: Observability dataclasses mutable vs frozen convention
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `logging_util` observability dataclasses are mutable while other cross-phase records are frozen, which may confuse Phase 2 authors about immutability/hash safety.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_19: subprocess timeout tests may flake under load
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Timeout tests use a 0.1s margin around `sleep(5)`; heavily loaded `python-tests` CI may flake on timeout assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_20: mutating gh helpers lack transient no-retry regression tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Beyond `pr_merge`, mutating gh helpers lack stub-runner single-call tests; future retry wrappers could regress without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_21: quiet breadcrumb tests cover suppression only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `quiet=False` and `LARCH_QUIET_DISABLE` paths are untested and could regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_22: make lint / pre-commit omit Python gates
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Local `make lint` and pre-commit can pass while `python-lint` CI fails; Python gates are not documented or hooked locally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_23: stdlib-only test misses dynamic non-literal imports
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: AST policy does not catch `importlib.import_module(variable)`; a future runtime module could add non-stdlib deps while the test stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_24: redact() trailing newline on gh body files
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Bash vs Python PR bodies may differ by one trailing newline on edge payloads for body-file writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_25: CI workflow plan drift (make vs inline python commands)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: CI jobs call `make py-lint`/`py-test` instead of plan-specified `working-directory: python` with inline linter commands; functionally similar today but future divergence may go unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_26: run_waterfall omits planned classify_fn parameter
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `run_waterfall` uses built-in `effective_failure_class` only; callers cannot inject alternate classification as the plan specified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_27: test_config immutability coverage incomplete
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Immutability tests cover only `TRANSIENT_RETRY_BACKOFF_SEC`, not other documented frozen tables such as `FIXER_TIER_ORDER`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### OOS_1: [OUT_OF_SCOPE] Gitleaks allowlist for python/test_redact.py and cache paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Gitleaks does not scan synthetic secret fixtures in `python/test_redact.py` and excludes python cache paths; accidental live secrets in allowlisted paths may skip layers 1–2. Documented tradeoff—rely on synthetic fixtures, discipline, and TruffleHog for live creds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] redact unit tests omit some GitHub token prefix families
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Tests omit vectors for some token prefix families (e.g. `gho_`/`github_pat_`), so regex drift in `redact.py` is less likely to be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] retry/agents ordering matches bash lib-net and launcher common
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: `retry.py` and `agents.py` match bash ordering guards, substring families, health/other/none mapping, and `parse_launcher_failure_class` whitelist parity with `scripts/ship-pr.sh:1696-1706` (positive parity note, not a defect).
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] redact() tmpdir-before-secrets chain matches canonical bash
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: Python `redact()` order matches canonical bash chain (`redact-tmpdir-paths.sh | redact-secrets.sh`); some legacy bash call sites still pipe secrets before tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] redact parity coverage thinner than bash harness
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: `python/test_redact.py` omits several single-line vectors from `scripts/test-redact-tmpdir-paths.sh`; multiline `$`-anchor gap (FINDING_15) is the material hole.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] mutating gh helpers intentionally omit read retry wrappers
- **Reviewer(s)**: dyn-gh-retry-policy-output.txt
- **Severity**: nit
- **Concern**: `pr_merge`, `run_rerun`, `issue_comment`, `issue_edit` call `_gh` directly—matches planned asymmetric retry policy.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] _body_file_args lifecycle and redaction before write
- **Reviewer(s)**: dyn-gh-retry-policy-output.txt
- **Severity**: nit
- **Concern**: Temp body files are written and unlinked safely; `redact()` runs before creation; `pr_create` parses stdout after context exit—no post-delete body read (positive note).
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] _redact_gh_scalar newline handling for scalar flags
- **Reviewer(s)**: dyn-gh-retry-policy-output.txt
- **Severity**: nit
- **Concern**: `_redact_gh_scalar` correctly strips `redact()` trailing newline for scalar gh flags while preserving intentional input newlines (positive note).
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] pr_create single create + one conflict list pass by design
- **Reviewer(s)**: dyn-gh-retry-policy-output.txt
- **Severity**: nit
- **Concern**: No internal create/list loop—intentional policy, not a defect in this branch.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_10: [OUT_OF_SCOPE] create-pr.sh wraps gh pr create in with_transient_retry by design
- **Reviewer(s)**: dyn-gh-retry-policy-output.txt
- **Severity**: nit
- **Concern**: Bash/Python divergence on create retry is plan-intentional (duplicate-create avoidance).
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_11: [OUT_OF_SCOPE] absent first_tier in tiers is intentional Python footgun
- **Reviewer(s)**: dyn-waterfall-semantics-output.txt
- **Severity**: latent
- **Concern**: When `first_tier` ∉ `tiers`, rotation is skipped and `tier_list[0]` is the policy tier; bash never hits this because it derives `first_tier` from the same array it iterates—document or require membership for Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_12: [OUT_OF_SCOPE] waterfall wrapper_rc == 0 requirement for short-circuit is intentional
- **Reviewer(s)**: dyn-waterfall-semantics-output.txt
- **Severity**: nit
- **Concern**: Matches bash and `test_waterfall_continues_on_wrapper_rc_2`; asymmetry vs `other` with nonzero `wrapper_rc` is intentional.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_13: [OUT_OF_SCOPE] waterfall success return on launcher_exit == 0 aligned with bash
- **Reviewer(s)**: dyn-waterfall-semantics-output.txt
- **Severity**: nit
- **Concern**: Success returns immediately with `winning_tier` set—aligned with bash `2069-2072`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_14: [OUT_OF_SCOPE] no unit test for bash run_ship_pr_2632_t4d three-tier cascade
- **Reviewer(s)**: dyn-waterfall-semantics-output.txt
- **Severity**: nit
- **Concern**: Manual trace suggests correct behavior for cursor health → codex other → claude still runs; colocated test would lock parity but implementation appears correct.
- **Suggested revisions (informational for voters; coder decides)**:
