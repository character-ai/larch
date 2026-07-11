# Discussion Round 1

Resolved scope decisions for issue #6864 (trusted-artifact contract completion). Source issue was filed as accepted OOS from the #6852 implement run (PR #6866).

## Decision 1: Fail-closed gate trigger
- **Question**: When `require_pr_mutation_scope_disposition` cannot find a valid trusted tmpdir (missing or not a directory), what should the ship-time gate do?
- **Resolution**: Context-gated fail. Fail closed only when an implement or ship context is detectable (such as `IMPLEMENT_TMPDIR` being set or a manifest being discoverable). Stay a no-op for standalone non-implement PR edits. If a context declares a tmpdir but it is missing or not a directory, treat that as an unsafe artifact state and raise, do not silently bypass the PR mutation gate.
- **Source**: user

## Decision 2: coder_runner migration depth
- **Question**: How far should the `coder_runner.py` snapshot migration go? It still calls the legacy `_snapshot_mode(round_dir)` heuristic the #6852 plan wanted removed.
- **Resolution**: Full validator routing. Route `coder_runner` through the complete-snapshot validator and drop the `_snapshot_mode` heuristic, as #6852 planned. Closes the trusted-artifact contract for this consumer.
- **Source**: user

## Decision 3: Regression test bar
- **Question**: What regression-test bar applies to the five unmigrated test files (`test_pr`, `test_pr_body`, `test_finalize`, `test_final_report`, `test_review_and_fix`)?
- **Resolution**: Full planned coverage. Add the coverage the #6852 plan listed for all five files, plus tests for the two defects this issue fixes (context-gated fail-closed behavior and coder_runner validator routing).
- **Source**: user

## Hard constraints (must not break)
- Legitimate standalone ship operations that run without an implement session tmpdir must keep working. The context-gated design exists to preserve this. Failing closed must be scoped to a detectable implement/ship context, not unconditional.
- Keep the existing trusted I/O primitives and snapshot locations from #6852. Extend the contract, do not redesign it.

## Non-goals
- Do not re-open or redo the full #6852 trusted-artifact migration. This issue only completes the leftover gaps: the fail-open gate, the `coder_runner` heuristic, and the five planned test files.
- No new opt-in flags or configuration knobs for the gate behavior. Detection is structural.

## Must-have requirements (minimum viable outcome)
- `require_pr_mutation_scope_disposition` no longer silently bypasses when a ship context exists but the trusted tmpdir is missing or invalid.
- `coder_runner.py` no longer relies on the unvalidated `_snapshot_mode` heuristic for decision paths.
- The five named test files gain the planned regression coverage.
