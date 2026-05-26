## Decision 1: Test coverage for Fix 1 (decompose-aggregator primary-tool swap)
- **Question**: The acceptance references `scripts/test-decompose-aggregator.sh` which does not exist. How should Fix 1 be regression-tested?
- **Resolution**: Create a small new harness at `skills/design/scripts/test-decompose-aggregator.sh` that asserts the aggregator builds its single-slot row with `tool="codex"` and threads `--require-result-pattern '^[[:space:]]*## Recommendation'`.
- **Source**: user

## Decision 2: Scope is locked to Fix 1 + Fix 2 only
- **Question**: Should sketch / plan-review collectors also adopt `--require-result-pattern`?
- **Resolution**: No. Explicit out-of-scope in issue body. Sketch tolerates narration-only as "no contested position"; plan-review has its own flow.
- **Source**: codebase (issue body Out of scope)

## Decision 3: Hard constraint — preserve existing exhausted-waterfall semantics
- **Question**: When --require-result-pattern is set and every tool fails the regex, should exit code / breadcrumb behavior change?
- **Resolution**: Treat pattern-mismatch as the same failure code path as STATUS!=OK (`failed+=("$idx")`); reuse the existing "all failed" exhaustion code path. No new exit codes.
- **Source**: codebase (issue body Fix 2 third bullet pins this path)
