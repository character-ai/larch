
Verifying a few cited locations so merged titles and concerns match the repo.
Structured finding list after merging duplicate reviewer slots. Positive security attestations (commits listed, injection checks passed) and affirmative OOS notes (design-skill suppression correct, plan self-reference gap accepted) are omitted — they are not actionable findings.

### FINDING_1: Makefile combined test target breaks test-compose-pr-summary
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-partial-flag-rendering-output.txt
- **Severity**: important
- **Concern**: A merged `test-compose-pr-summary test-compute-pr-line-counts` rule runs `bash scripts/harness-timer.sh $@ bash scripts/test-compose-pr-summary test-compute-pr-line-counts.sh`, omitting `.sh` on the compose harness and passing `test-compute-pr-line-counts.sh` as a stray argument. `make test-compose-pr-summary` (including via `test-harnesses-4`) fails (e.g. exit 127), breaking CI shard 4 coverage for the PR summary composer. A standalone `test-compute-pr-line-counts` recipe exists but the combined rule masks/conflicts with correct per-target recipes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Split into separate targets: test-compose-pr-summary -> bash scripts/harness-timer.sh $@ bash scripts/test-compose-pr-summary.sh; keep standalone test-compute-pr-line-counts target
  - From cursor-specialist-correctness-output.txt: Split into standalone test-compose-pr-summary and test-compute-pr-line-counts targets each with harness-timer.sh $@ bash scripts/test-<name>.sh; delete the combined multi-target rule
  - From cursor-specialist-plan-fidelity-output.txt: Split the two targets back into independent rules; remove the combined `test-compose-pr-summary test-compute-pr-line-counts:` multi-target rule entirely.
  - From dyn-partial-flag-rendering-output.txt: Restore separate single-target recipes (`test-compose-pr-summary` → `scripts/test-compose-pr-summary.sh`; `test-compute-pr-line-counts` → `scripts/test-compute-pr-line-counts.sh`), delete the broken combined target, and remove the duplicate `test-compute-pr-line-counts` prerequisite on `Makefile:81`.

### FINDING_2: Duplicate test-compute-pr-line-counts on test-harnesses-4
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-partial-flag-rendering-output.txt
- **Severity**: nit
- **Concern**: `test-compute-pr-line-counts` is listed twice on the `test-harnesses-4` prerequisite line (`Makefile:81`), so shard 4 runs the same harness twice per CI cycle without added coverage and may trip harness-shard drift checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove the duplicate test-compute-pr-line-counts token from the test-harnesses-4 line
  - From cursor-specialist-plan-fidelity-output.txt: Remove the duplicate entry, keeping a single `test-compute-pr-line-counts` in `test-harnesses-4`.
  - From dyn-partial-flag-rendering-output.txt: Remove the duplicate `test-compute-pr-line-counts` prerequisite on `Makefile:81`.

### FINDING_3: render-run-summary partial line-count flags produce malformed Lines bullet
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-partial-flag-rendering-output.txt
- **Severity**: latent
- **Concern**: At `scripts/render-run-summary.sh:216-218`, `lines_disp` uses OR across the four counters but always interpolates all four into the format string. A caller passing only some `--code-*` / `--logs-*` flags can render a malformed Lines bullet (e.g. `code +107/-, larch-logs +/-/`). `write-final-report.sh` gates all four integers on the production path today, but the shared renderer and `scripts/render-run-summary.md` do not require all-or-nothing input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Require all four counters before formatting; default to N/A otherwise.
  - From dyn-partial-flag-rendering-output.txt: Change the renderer condition to require all four non-empty integer values (mirror `LINES_DATA_OK` in `skills/implement/scripts/write-final-report.sh:127-147`), update `scripts/render-run-summary.md` to state all-or-nothing explicitly, and add a harness case in `scripts/test-render-run-summary.sh` that passes a partial flag set and expects `N/A`.

### FINDING_4: Duplicated read_lines_kv / KV parsing in write-final-report.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `read_lines_kv` and nested `case` integer checks at `skills/implement/scripts/write-final-report.sh:111-147` duplicate existing `read_kv` style, making consistent KV parsing harder to maintain across `write-final-report.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate parsing/validation into a small shared helper.

### FINDING_5: Duplicated gh PR /files TSV shim across test harnesses
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The `gh` PR files shim at `scripts/test-compute-pr-line-counts.sh:35-52` is duplicated in `skills/implement/scripts/test-write-final-report.sh`, risking fixture drift if one harness updates TSV rows and the other does not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared test fixture for gh and /files TSV output.

### FINDING_6: No integration test for gh-failed line-count degradation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/scripts/test-write-final-report.sh` has no end-to-end fixture for `gh` API failure with nonzero PR and repo available; `gh-failed` degradation in `write-final-report.sh` is untested at the integration layer despite plan acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fixture: GH_SHIM_FAIL=true, PR_NUMBER set, REPO_UNAVAILABLE=false; assert Lines N/A and STATUS=ok

### FINDING_7: test-render-run-summary only greps partial Lines prefix
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: At `scripts/test-render-run-summary.sh:75`, the primary implement test only greps a partial Lines bullet prefix; wrong `larch-logs` segment or numeric values could regress undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert full expected line string with all four counters

### FINDING_8: compute-pr-line-counts discards gh stderr on API failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: At `scripts/compute-pr-line-counts.sh:50`, `gh` stderr is discarded on API failure. Operators see only `Lines (PR diff): N/A` with no hint whether failure was auth, network, or bad repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Consider surfacing REASON detail to stderr or logging a warning without aborting the report.

### FINDING_9: Missing or non-executable compute-pr-line-counts.sh fails silently to N/A
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: At `skills/implement/scripts/write-final-report.sh:118-126`, a missing or non-executable `compute-pr-line-counts.sh` degrades to N/A without an execution-issues warning, which can mask a broken plugin install or chmod regression as “no data PR.”
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Append a Warnings entry when helper invocation fails and PR_NUMBER is nonzero.

### FINDING_10: Bucketed fixture asserts content-lines.md not summary-final.md
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: At `skills/implement/scripts/test-write-final-report.sh:1167`, the bucketed-fixture (`impl_lines`) assertion checks `content-lines.md` (TRACKING_CONTENT_LOG) rather than `summary-final.md` as the plan specifies. The `REPO_UNAVAILABLE` fixture at line 1197 correctly checks `summary-final.md`. Both receive the same summary content so this is likely not a functional failure, but plan coverage for happy-path `summary-final.md` is indirect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add `assert_contains '- **Lines (PR diff)**: code +17/-3, larch-logs +5/-1' "$(cat "$impl_lines/summary-final.md")"` alongside the existing `content-lines.md` assertion, mirroring the pattern used by the `REPO_UNAVAILABLE` fixture at line 1197.

### FINDING_11: [OUT_OF_SCOPE] PR_NUMBER/REPO not validated before gh api path build
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-api-input-safety-output.txt
- **Severity**: latent
- **Concern**: At `scripts/compute-pr-line-counts.sh:33-42` (and call sites in `write-final-report.sh`), `PR_NUMBER` and `REPO` are interpolated into the `gh api` REST path with only empty/`0` skipping. There is no `^[0-9]+$` check on `PR_NUMBER` and no `validate_repo`-style guard on `REPO`. In normal runs values come from session setup / create-pr, but tampered `ship-pr-state.sh`, `session-env.sh`, or direct CLI invocation could supply odd values and trigger unexpected `gh api` paths or failures (degraded to `N/A`, not RCE).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reject values that do not match `^[0-9]+$` for `--pr-number` and `^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$` for nonempty `--repo` before calling `gh`, mirroring the `RUN_ID` rejection pattern in `write-final-report.sh`.
  - From dyn-api-input-safety-output.txt: Before building `endpoint`, reject non-digit `PR_NUMBER` (emit `LINES_STATUS=skipped` with `REASON=invalid-pr` or `unavailable`) and apply the existing `validate_repo` pattern used in `scripts/upsert-diagrams-comment.sh:116-124` for nonempty `REPO`; mirror the same checks in `skills/implement/scripts/write-final-report.sh:118-119` before invoking the helper, consistent with `RUN_ID` path rejection at `write-final-report.sh:79-83`.

### FINDING_12: [OUT_OF_SCOPE] write-final-report validates RUN_ID but not PR_NUMBER/REPO at new gh call site
- **Reviewer(s)**: dyn-api-input-safety-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/scripts/write-final-report.sh:79-83` fail-closes on path-metacharacters in `RUN_ID` but do not apply analogous validation to `PR_NUMBER`/`REPO` at the new helper call site (`118-119`); pre-existing gap amplified by this branch’s first `gh api` use from final-report wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-api-input-safety-output.txt: (Covered by FINDING_11 dyn-api fix — mirror `RUN_ID` rejection and `validate_repo` at the `write-final-report.sh` call site before invoking the helper.)
