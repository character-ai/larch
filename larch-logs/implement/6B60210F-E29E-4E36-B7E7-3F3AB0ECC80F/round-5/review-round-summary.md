# Review Round 5

- Mode: `diff`
- 8 accepted, 19 rejected (17 exonerated)

## Accepted Findings

### FINDING_1: Plan acceptance vs live ship-pr.sh Python replay wiring
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch adds live `scripts/ship-pr.sh` changes (python-lint/python-tests job argv mapping and local CI replay) while plan/acceptance still claims `ship-pr.sh` is untouched and zero live-path change. Acceptance criteria and the plan should explicitly list `ship-pr.sh` replay wiring, or defer that wiring until the Python cutover phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


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


### FINDING_8: relevant-checks skips Python gates when toolchain absent
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When python tools are missing from PATH, `scripts/relevant-checks.sh` skips `py-lint`/`py-test` with exit 0. `/implement` Step 5 can pass on python-only diffs without running pytest/linters; regressions surface only in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Fail closed when python/*.py changes and toolchain absent, or auto pip install requirements before running make targets
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


