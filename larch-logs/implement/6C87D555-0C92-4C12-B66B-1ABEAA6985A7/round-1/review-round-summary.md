# Review Round 1

- Mode: `diff`
- 4 accepted, 8 rejected (7 exonerated)

## Accepted Findings

### FINDING_1: compose_prompt excerpt mktemp failure bypasses fail_status / LINT_FIX_STATUS
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Under `set -e`, `compose_prompt` returns 1 when excerpt `mktemp` fails (e.g. `/tmp` exhaustion at lines 145–146) and the top-level caller invokes it without `fail_status` (line 526). The script exits with bare status 1 and no `LINT_FIX_STATUS=failed`, so upstream implement/ship-pr logic cannot classify the failure.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_2: Generic slash-path grep pollutes ## In-scope files
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The fifth grep pattern (line 111) matches generic `dir/file` tokens anywhere in the excerpt. Any log mention of an existing but unrelated path (e.g. prose referencing `scripts/relevant-checks.sh` while the failure is in `scripts/lint-fix-loop.sh`) can land in `## In-scope files` and misdirect the external coder despite log-scoped `fix_sentence`. Narrow or remove the slash-only pattern; rely on shellcheck, `path:line`, and extension patterns, or gate the broad regex behind empty results from stricter extractors.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_3: affected_files_from_log errors swallowed in process substitution
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Inside `compose_prompt`, `affected_files_from_log` runs in a process substitution (lines 150–153) while failures there may not abort under `set -e`. `mktemp` failure or other extractor errors can yield an empty `affected_list` and the empty-list `fix_sentence` without surfacing parse failure, so Codex may miss in-scope paths and anti-cascade guidance even when the log shows concrete shellcheck paths.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_4: Missing test for phase-gated absence of optional pre-commit hint
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No harness case asserts that optional pre-commit verification is suppressed for agent-lint or direct-make phases. A regression could re-enable pre-commit hints on non-pre-commit failures while existing cases (e.g. Case 12) still pass, leading coders to run scoped pre-commit and hit whole-repo hooks. Add a case with `=== Running agent-lint ===` (or direct-make banner) plus a parseable `In … line …` failure; assert in-scope list present and optional pre-commit block absent.
- **Suggested revisions (informational for voters; coder decides)**:


