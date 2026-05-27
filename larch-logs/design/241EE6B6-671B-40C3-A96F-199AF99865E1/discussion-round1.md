## Decision 1: Scope — combine Task 1 and Task 2
- **Question**: Should this design cover both the Cursor `--mode plan` root-cause fix AND the deferred `normalize_rcc_max_iter` carry-over patches?
- **Resolution**: Both tasks in a single plan.
- **Source**: user

## Decision 2: Cursor fix layering
- **Question**: Of the three fix layers proposed in the issue (primary `--mode plan` → `--mode ask`, secondary length-vs-tokens backstop, tertiary `--require-result-pattern` opt-in), which are in-scope for this `--simple` design?
- **Resolution**: All three layers — primary + secondary + tertiary.
- **Source**: user

## Decision 3: Secondary backstop thresholds
- **Question**: Are the issue's proposed thresholds (`usage.outputTokens > 1000` AND extracted `.result` < 500 bytes) acceptable verbatim?
- **Resolution**: Use proposed thresholds verbatim. No env-knob configurability in this PR.
- **Source**: user

## Decision 4: `--mode plan` production callsite scope
- **Question**: Are there any production callsites passing `--mode plan` other than `scripts/launch-review.sh:924`?
- **Resolution**: Only `scripts/launch-review.sh:924`. The other `--mode plan` references in the codebase are: line 830 (comment block, Issue #1529), line 843 (`CURSOR_SANDBOX_ENFORCEMENT_LINE` injected into the prompt preamble), `scripts/validate-research-output.sh:435` (comment only), `scripts/launch-review.md:29` (doc), and `scripts/test-launch-review.sh` lines 1827/1838/1887/1890/1960 (tests pinning the literal flag in the argv).
- **Source**: codebase

## Decision 5: Test-side `--mode plan` references
- **Question**: Which test cases pin `--mode plan` as a literal argv string and require updating?
- **Resolution**: `scripts/test-launch-review.sh` cases at lines 1827, 1838, 1887, 1890, 1960. The Issue #1529 / #1583 grammar tests must continue to assert the `cursor` argv carries the read-only mode flag, but now `--mode ask`. The CURSOR_SANDBOX_ENFORCEMENT_LINE assertion at line 1887 must match the updated launcher-side string.
- **Source**: codebase

## Decision 6: Tertiary `--require-result-pattern` scope
- **Question**: Should tertiary cover both sketch dispatch and plan-review panel dispatch, or only one of them?
- **Resolution**: **Plan-review only.** Reviewer output reliably starts with either the TSV header `schema_version` or the single-line JSON sentinel `{"no_issues_found": true}`, so the pattern gate has near-zero false-positive risk on healthy runs. Sketches lead with prose and would risk false-negative fallback. The secondary length-vs-tokens backstop covers the sketch surface.
- **Source**: user

## Decision 7: `CURSOR_DEGRADED_RESPONSE` observability
- **Question**: When the backstop fires, should the operator see a chat breadcrumb, or rely on the existing collector telemetry path only?
- **Resolution**: Telemetry-only via existing collector path. The launcher writes the sentinel; `collect-agent-results.sh` reports `STATUS != OK` and logs `External Reviewer Issues` per the standard pipeline; waterfall fallback fires automatically. No new chat breadcrumb. Matches `CURSOR_EMPTY_RESPONSE` semantics.
- **Source**: user

## Decision 8: Cursor read-only safety property (hard constraint)
- **Question**: Does switching `--mode plan` → `--mode ask` preserve Cursor's read-only safety property?
- **Resolution**: Yes. Per `cursor agent --help` (cited verbatim in the issue body), both `plan` and `ask` modes are documented read-only. The launcher's existing dirty-tree sidecar (snapshot-untracked.sh baseline + `_write_dirty_tree_sidecar` EXIT trap) remains the after-the-fact backstop and is unchanged by this PR. Issue #1529's prompt-preamble HARD CONSTRAINTS remain unchanged.
- **Source**: codebase + user

## Decision 9: Task 2 patch verification (acceptance criterion)
- **Question**: Should the Task 2 `test-ship-pr.sh` rewrite (which removes the `vendor-verify-sweep.sh` helper-stub indirection and replaces it with a direct `ship-pr.sh` integration call gated by `STUB_LINT_FIX_STATUS=main-agent-required`) require a passing test as an acceptance criterion?
- **Resolution**: Yes. Acceptance criterion includes `vendor_verify_sweep_regression` still asserting exit 4 + `STALL_STEP=10-max-retries` + zero pushes after the helper-stub removal. Plus existing `_RCC_MAX_ITER`-stub cases still pass after the `normalize_rcc_max_iter` insertion.
- **Source**: user

## Decision 10: Task 2 patch context still applies (hard constraint check)
- **Question**: Does the issue's verbatim diff still apply cleanly against the current `scripts/ship-pr.sh` / `scripts/test-ship-pr.sh`?
- **Resolution**: Yes (with fuzz). Current line numbers: `ship-pr.sh:2013` and `:2118` (issue body shows 2010/2115, off-by-3 from fixed-context counting); `test-ship-pr.sh` vendor-verify-sweep block at lines 3647-3658 (issue body shows 3644-3658), and `_RCC_MAX_ITER` stub bodies at 3786/3830/3876 (issue body shows 3783/3827/3873). Surrounding context lines are byte-identical; the patch should apply with `git apply --3way` or under a regular fuzzy patch tool.
- **Source**: codebase

## Decision 11: `normalize_rcc_max_iter` already exists
- **Question**: Does `normalize_rcc_max_iter` exist as a function in `ship-pr.sh` (so the patch sites can call it without defining it)?
- **Resolution**: Yes, defined at `scripts/ship-pr.sh:162`. Already in use at `run_captured_cmd_then_fix_loop` (per #2998). Task 2 just extends usage to `_verify_failed_jobs_locally` and `run_per_job_local_fix_loop` plus three test-stub bodies.
- **Source**: codebase
