# Discussion Round 1

## Decision 1: PR structure
- **Question**: Should Items A and B ship as a single PR or split into two PRs?
- **Resolution**: Single PR covering both items. Both items are independent, ~30 LOC each, in shell scripts, and the issue body explicitly combines them under OOS triage rule 3.
- **Source**: user (Step 1c)

## Decision 2: Item B sanitization policy
- **Question**: For `ci-failed-jobs.sh` line 80 stderr passthrough, use the strict `sanitize_list` whitelist or a permissive whitelist that preserves human-readable diagnostics?
- **Resolution**: Permissive whitelist that strips control bytes and newlines while preserving spaces, ASCII printable punctuation, and standard diagnostic characters so `gh run view` stderr remains human-readable.
- **Source**: user (Step 1c)

## Decision 3: Item B audit scope
- **Question**: Beyond line 80, what other emit sites should the plan address?
- **Resolution**: Full `ci-failed-jobs.sh` audit for raw job-name emit sites; do not expand into callers that surface `FAILED_JOBS_*` into prompts. The other two `larch_err` calls in the file (`usage()` at line 16 and `die()` at line 20) take internal literal strings and need no sanitization.
- **Source**: user (Step 1c) + codebase

## Decision 4: Test coverage
- **Question**: Should the plan extend existing test coverage for both files?
- **Resolution**: Yes. Both `skills/implement/scripts/test-generate-code-flow-diagram.sh` and `scripts/test-ci-failed-jobs.sh` exist with matching `.md` siblings. The plan must add regression cases (multi-`=` token for SKIP_REASON; control-byte/newline inputs for the stderr passthrough) and keep both harnesses passing.
- **Source**: codebase

## Decision 5: Preserve `larch_err` per-line passthrough semantics
- **Question**: Must the existing `while IFS= read -r line ... larch_err "$line"` loop structure remain (one log line per stderr line)?
- **Resolution**: Yes. Downstream operators read each stderr line as a distinct diagnostic; the sanitization fix must be inline per-line and must not collapse the loop into a single emit.
- **Source**: codebase

## Decision 6: Preserve `SKIP_REASON` fallback chain
- **Question**: Must `|| printf 'sanitizer-rejected'` remain the fallback when no `REASON_TOKEN` line is present in `$sanitize_log`?
- **Resolution**: Yes. The fallback is the existing contract for downstream `step-7a` consumers; the awk-parsing fix must change only how the token value is captured when `REASON_TOKEN=` IS present.
- **Source**: codebase
