# Review Round 1

- Mode: `diff`
- 6 accepted, 6 rejected (0 neutral)

## Accepted Findings

### FINDING_1: malformed push command in the CI-fix path
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-ci-fixer-flow
- **Severity**: major
- **Concern**: The kill-switch inline CI-fix path rewrites the push step into a malformed shell token, so the branch push fails on the kill-switch path and on the post-bail reuse path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Restore python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" push branch and fix harness needles
  - From codex-specialist-correctness: Replace it with a valid `python/cli.py push branch` command, preferably using `${CLAUDE_PLUGIN_ROOT}/python/cli.py`.
  - From cursor-specialist-edge-cases: Use python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" push branch.
  - From codex-specialist-edge-cases: Use python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" push branch.
  - From dyn-dyn-ci-fixer-flow: Restore the full plugin-rooted push invocation in `ship-pr-ci-fix.md`, mirror it in post-bail prose, and update both structure harnesses to require the corrected command instead of the typo.


### FINDING_2: failed-job distillation can collapse distinct jobs into one bucket
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The distill-log pipeline can collapse multiple failed jobs into one bucket because dedupe is global, truncation is global, and the parser only understands a synthetic line format; that can hide later failing jobs from the fixer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Scope dedupe per job or matrix family instead of content-only global fingerprint
  - From codex-specialist-edge-cases: Preserve a per-job index, cap per job before global assembly, and dedupe by listing all affected job names.
  - From cursor-specialist-testing: Add a distill-log test stubbing three failed jobs in JSON but only one in --log-failed; assert placeholder sections and FAILED_JOBS_COUNT.
  - From codex-specialist-testing: Parse the real GitHub log boundaries from the raw --log-failed stream or reuse an existing splitter, then add a fixture that matches the true output format.


### FINDING_7: GitHub/log health failures are collapsed into the generic log-failure class
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Health failures such as gh auth, quota, or binary lookup errors are folded into the generic GitHub log failure class, which sends them down inline repair instead of an early operator bail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Classify health failures before the generic case, emit a health bail class or `ci-fixer-health-bail`, and return a distinct health exit code.
  - From codex-specialist-edge-cases: Emit explicit health bail classes and route them directly to operator-bail.


### FINDING_8: `in_progress` is treated like a fallback case instead of a transient wait state
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-ci-fixer-flow
- **Severity**: minor
- **Concern**: `STATUS=in_progress` / `BAIL_CLASS=in_progress` is treated like a fallback case even though the logs are just not ready yet, so the fallback budget can burn without fresh evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Route BAIL_CLASS=in_progress to operator-bail or a bounded wait; do not count it as a fallback repair attempt.
  - From dyn-dyn-ci-fixer-flow: Map `BAIL_CLASS=in_progress` to a bounded distill retry or operator-bail; reserve post-bail fallback for fixer bail/exhaustion or non-transient distill errors (`github-log-failure`, `write-failure`). Document the `BAIL_CLASS` table explicitly and add a harness/test row for the in-progress branch.


### FINDING_11: digest redaction happens after truncation
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The digest is truncated before redaction, so a token that straddles the byte cap can leave an unredacted prefix in the distilled failure file or later bailout context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Redact the full digest first, cap the redacted text, then run a final scrub check before writing.


### FINDING_17: distill-log uses the same exit code for health failures and write failures
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: The CLI maps both GitHub/log health failures and digest write failures to the same exit code, which makes it impossible for wrappers to distinguish the two bailout classes without scraping stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add a dedicated rc for write failure or otherwise map each bailout class to a unique exit code, and test the distinction.


