## Goal
Implement issue #7097: [IMPLEMENTING] [BUG] Architectural assessment lacks a fallback waterfall for transient tool failures.

## Implementation Plan
## Plan

## Approach

- Register `implement.architectural_assessment` as a canonical waterfall role ordered Cursor/Composer-2.5, Codex/Terra, then Claude/Sonnet-4-6.
- Reuse shared read-only external launch, authentication, model resolution, timeout, availability, dirty-tree, and result-sidecar machinery. Add assessment-contract options only; do not introduce a second selector.
- Resolve Codex, Cursor, and Claude availability from `$IMPLEMENT_TMPDIR/session-env.sh` before selection, using the environment/session-file/`shutil.which` fallback semantics of `checks_lint_fix._binary_flag`. Pass all three flags to `next_untried_tier`; never let runtime PATH drift override recorded session availability.
- Run unresolved kinds through available lanes in order. Persist every valid kind immediately and omit it from later prompts.
- Give Cursor a read-only assessment workspace containing the validated evidence directory, while separately baselining the repository for its dirty-tree sidecar. Give Codex the validated evidence directory through `--add-dir` while retaining the repository working directory/baseline; neither lane may rely on ungranted evidence paths.
- Require `STATUS=clean` before accepting Cursor output; dirty, missing, malformed, or unknown sidecars make that lane unavailable.
- Keep Claude’s established direct read-only invocation: `claude --print --model claude-sonnet-4-6 --add-dir <evidence-dir> --allowedTools Read --permission-mode plan`.
- Add an assessment mode to the shared Codex/Cursor launcher that uses the assessment prompt verbatim, preserves the extracted raw result payload for the coordinator parser, bypasses review-only Cursor degradation/no-issues normalization, and disables same-lane auth, transient, timeout, and empty-response retries.
- Advance only on unavailable-class failures: unavailable binary, non-zero underlying launcher exit, timeout, empty output, malformed launcher metadata or sidecars, dirty/unknown Cursor tree, malformed envelope or row, or an omitted kind.
- Stop a kind on any valid authored result, including violations and deviations. Preserve existing `re-author-required`, deterministic-clean, handled, persistence, HEAD-drift, and stdout semantics.
- Persist `unavailable` only after all available lanes fail. Store that kind’s final sanitized diagnostic.
- Increase the bgjob budget to cover three sequential lane timeouts plus launcher, sidecar, daemon, and publication overhead. Keep the adapter’s second child attempt limited to child-envelope or daemon failure, separate from lane selection.

## Edge cases

- Recorded Cursor, Codex, or Claude absence skips that lane before launch; recorded presence attempts it even if `shutil.which` would differ later.
- Cursor evidence is reachable through its assessment workspace without staging files in or granting write access to the repository.
- Codex receives the validated evidence directory through an explicit read-only `--add-dir`; all evidence paths named in its prompt must be contained by granted add-dir roots.
- Cursor success with a dirty, unknown, missing, or malformed dirty-tree sidecar is never persisted; the next lane receives only unresolved kinds.
- Codex or Cursor review postprocessing must not rewrite a valid compact assessment JSON result as degraded, empty, or `NO_ISSUES_FOUND`.
- Claude missing: skip it like any unavailable binary and persist `unavailable` after no lanes remain.
- Mixed response: persist valid kinds, then send only malformed or omitted kinds to the next lane.
- Invalid explicit outcome metadata: retain the current `re-author-required` result instead of treating a produced assessment as transient.
- HEAD drift: discard the in-flight waterfall result and rematerialize through the existing recursive drift path.
- All lanes fail differently: retain the last attempted diagnostic per kind, redact secrets and tmpdir paths, and keep the existing 500-character handoff bound.
- A valid violation or deviation from the first lane must not be overwritten by a later lane.

## Failure modes

- Fail closed if shared launcher metadata, output sidecars, Cursor dirty-tree sidecars, evidence-workspace paths, or Codex evidence add-dir validation cannot be validated.
- Do not accept wrapper exit success when the underlying launcher reports failure, an empty result, malformed output, or a non-clean Cursor tree.
- Do not let shared launcher auth or transient-response retries multiply the one-attempt-per-lane contract.
- Keep the existing operator-bail route and `ASSESSMENT_RESULTS` grammar unchanged.

### UPDATED: python/larch/core/config.py

- Add the `implement.architectural_assessment` waterfall role with order `("cursor", "codex", "claude")`.
- Pin Composer-2.5, Terra, Sonnet-4-6, and the per-lane timeout through existing model constants or new assessment-specific `Final` constants rather than duplicating literals.

### UPDATED: python/larch/core/external_defaults.py

- Use the existing waterfall resolver for assessment lane availability and exhaustion.
- Extend only typed role support needed by the assessment coordinator. Do not create a second selection algorithm.

### UPDATED: python/larch/agents/_review_launcher.py

- Expose the shared read-only Codex and Cursor launch path for an assessment contract without injecting review output instructions or review-specific Cursor prompt wrapping.
- Add a bounded single-attempt mode that disables transient, empty-response, timeout, and auth retry loops for this caller.
- Add assessment workspace and repository-baseline inputs: Cursor launches with the validated evidence directory as its workspace and writes its dirty-tree sidecar against the repository baseline.
- In Codex assessment mode, retain the repository working directory/baseline and pass the validated evidence directory as an explicit `--add-dir`, validating that prompt-referenced evidence paths remain under granted add-dir roots.
- In assessment mode, extract and return Cursor’s result payload verbatim for architectural-assessment parsing; bypass review-only degraded-response, no-issues, and normalization postprocessing.
- Return or persist canonical underlying launcher exit, raw output, diagnostic, and dirty-tree-sidecar data so the assessment adapter can distinguish success from wrapper-level exit zero.
- Preserve existing review behavior when the new mode is absent.

### UPDATED: python/tests/agents/test_launch_review.py

- Verify assessment mode uses Codex `--sandbox read-only` with Terra and Cursor `--mode ask` with Composer-2.5.
- Verify the assessment prompt contract replaces review-specific instructions, Cursor’s workspace is the validated evidence directory, and Codex retains the repository baseline while receiving that evidence directory through `--add-dir`.
- Verify Codex prompt evidence paths are within its granted add-dir root and are not left inaccessible through a repository-only workspace.
- Verify a valid compact Cursor assessment JSON is extracted verbatim, bypasses review degradation normalization, and is available to stop later lanes.
- Verify single-attempt mode does not retry empty output, timeout, non-zero exit, transient failure, or auth failure.
- Verify assessment-mode Cursor emits a repository-baselined `STATUS=clean` dirty-tree sidecar after a clean run and preserves dirty or unknown status for coordinator rejection.
- Retain regression coverage that ordinary review launches keep their current retry policy and postprocessing.

### UPDATED: python/larch/implement/architectural_assessment.py

- Replace `_MODEL`, `_EMPTY_STDOUT_ATTEMPTS`, `ClaudeLauncher`, and the one-command `_launch_assessment` flow with typed lane definitions and injected per-tool launch adapters.
- Resolve `CODEX_BINARY_FOUND`, `CURSOR_BINARY_FOUND`, and `CLAUDE_BINARY_FOUND` from the process environment, then `$IMPLEMENT_TMPDIR/session-env.sh`, then binary discovery, matching `checks_lint_fix._binary_flag` semantics. Pass those values to `next_untried_tier` for `implement.architectural_assessment`.
- Resolve available lanes through that role and treat skipped unavailable lanes as unattempted.
- Build one validated evidence directory, then create a fresh prompt and result artifact for the unresolved kinds at each lane.
- Launch Cursor and Codex through assessment-mode shared adapters; give Cursor the evidence workspace and validate its dirty-tree sidecar is a regular, trusted `STATUS=clean` record before parsing its output.
- Pass the same validated evidence directory to the Codex assessment adapter as its explicit `--add-dir`, and reject a launch contract whose prompt evidence paths fall outside its granted roots.
- Preserve the current Claude lane’s `--print`, model, evidence `--add-dir`, `--allowedTools Read`, and `--permission-mode plan` argv shape, while enforcing one subprocess attempt and the per-lane timeout.
- Parse results independently. Persist valid rows and remove those kinds from the pending set before advancing.
- Classify empty output, malformed JSON or rows, omitted kinds, timeout, non-zero underlying exit, invalid launcher data, unavailable binaries, and non-clean Cursor sidecars as lane-unavailable.
- Keep invalid explicit outcome handling on the current `re-author-required` path.
- Track the latest bounded diagnostic per pending kind. Call `_persist_unavailable` only after the waterfall is exhausted.
- Preserve stale-input validation, HEAD-drift rematerialization, deterministic skips, durable-note validation, violation preservation, and stdout grammar.

### UPDATED: python/tests/implement/test_architectural_assessment.py

- Replace same-Claude empty-output retry tests with ordered waterfall tests.
- Reproduce the reported empty primary response and prove Cursor failure advances to Codex, while a Codex result prevents Claude launch.
- Cover Cursor to Codex to Claude ordering and exactly one launch per available lane.
- Cover session-env availability flags for all three vendors, including a recorded absent external skipped despite PATH availability and a recorded present external attempted despite `shutil.which` drift.
- Cover missing binaries, non-zero exits, timeouts, empty output, invalid JSON, malformed rows, malformed launcher data, and full exhaustion.
- Cover Cursor evidence-workspace access, Codex evidence `--add-dir` forwarding and prompt-root validation, acceptance of an exact valid JSON result, and rejection/fallback for dirty, unknown, missing, or malformed Cursor dirty-tree sidecars.
- Assert the Claude lane retains `--print`, `--add-dir`, `--allowedTools Read`, and `--permission-mode plan`.
- Cover per-kind independence: one kind succeeds while the other advances, and later prompts contain only unresolved kinds.
- Assert a valid violation or deviation stops its kind and is not overwritten.
- Assert invalid explicit outcome metadata remains `re-author-required`.
- Assert the final unavailable receipt and outcome contain the last lane’s sanitized diagnostic.
- Keep HEAD-drift, stale coverage, result ordering, and stdout contract tests.

### UPDATED: skills/implement/scripts/step-8-assessment.sh

- Raise `BUDGET_S` from the single-lane allowance to the bounded three-lane allowance plus launcher, daemon, and publication overhead.
- Leave availability resolution and lane selection in Python. Keep Bash limited to bgjob identity, wait, envelope validation, and child-process retry handling.
- Preserve `ASSESSMENT_RESULTS`, `ASSESSMENT_STATUS`, and operator-bail handoff behavior.

### UPDATED: skills/implement/scripts/step-8-assessment.md

- Document the three-lane worst-case budget, session-recorded availability, and Python-owned per-kind waterfall.
- Clarify that adapter attempt 2 repairs child or daemon failure and does not add same-tool model retries.

### UPDATED: skills/implement/scripts/test-step-8-assessment.sh

- Update static and runtime budget pins.
- Assert the adapter still invokes one Python coordinator per child and does not implement tool selection or availability probing.
- Retain timeout, rejoin, stale identity, fail-closed, and no-attempt-3 coverage.

### UPDATED: skills/implement/scripts/test-step-8-assessment.md

- Update the documented budget expectations and distinguish adapter retries from model-lane attempts.

### UPDATED: python/tests/core/test_external_role_defaults.py

- Pin `implement.architectural_assessment` as an independent Cursor to Codex to Claude waterfall role.
- Test availability skipping and exhaustion through the existing resolver, including explicit Claude absence.

### UPDATED: docs/external-reviewers.md

- Add Step 8 architectural assessment to the role table with its exact tool and model order.
- State that session-recorded binary availability controls lane skipping, Cursor reads validated assessment evidence in a read-only workspace, Codex receives that evidence through a read-only add-dir, and each kind stops on its first parseable assessment.
- State that operator-bail occurs only after all available lanes fail.

## Testing strategy

- Run `python3 -m pytest python/tests/implement/test_architectural_assessment.py`.
- Run focused shared-launcher tests in `python/tests/agents/test_launch_review.py`.
- Run `python3 -m pytest python/tests/core/test_external_role_defaults.py`.
- Run `bash skills/implement/scripts/test-step-8-assessment.sh`.
- Run Python lint and type checks only for the changed Python files.
- Run Bash 3.2 and shell checks only for the changed Step 8 scripts.

## Acceptance

- Run `python3 -m pytest python/tests/implement/test_architectural_assessment.py`.
- Run focused shared-launcher tests in `python/tests/agents/test_launch_review.py`.
- Run `python3 -m pytest python/tests/core/test_external_role_defaults.py`.
- Run `bash skills/implement/scripts/test-step-8-assessment.sh`.
- Run Python lint and type checks only for the changed Python files.
- Run Bash 3.2 and shell checks only for the changed Step 8 scripts.

oversize_override: operator
diff_lines: 860

## Test plan
(no test plan section in plan-file)
