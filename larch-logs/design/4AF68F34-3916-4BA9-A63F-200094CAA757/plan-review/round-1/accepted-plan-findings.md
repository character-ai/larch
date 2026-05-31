### FINDING_1: Unguarded `mktemp` can abort cleanup before count KVs
- **Reviewer(s)**: Codex-Edge, Codex-Innovation
- **Severity**: important
- **Concern**: The planned temp-file enumeration wraps `find` with `mktemp`-backed lists. Under `set -e`, if `TMPDIR` (or the default temp location) is missing or unwritable, `mktemp` exits non-zero before any guarded `find` failure branch runs. Cleanup then aborts without emitting the required removal-count key-values, contradicting the planned fail-safe where `/cleanup` still exits 0 when enumeration fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Guard each mktemp call: on allocation failure, emit a larch_err warning, skip that pass with count 0, and continue to the next pass; or fall back to /tmp before deciding to skip
  - From Codex-Innovation: Guard mktemp failure and warn/skip that pass, or use a known writable fallback; add one focused harness case for bad TMPDIR


### FINDING_3: Removing loop-level `|| true` changes loop-body failure semantics
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-cleanup-fail-safe
- **Severity**: important
- **Concern**: The plan drops the `|| true` on the two `while read` loops (lines 55–61 and 99–110 in the proposed shape) as redundant after moving `find` into an `if` branch. In Bash, that `|| true` on the process-substitution pipeline also suppresses errexit for failures inside the loop body (e.g. `rm` failures). Removing it changes behavior beyond top-level enumeration `find` failures: `/cleanup` can exit non-zero and skip planned temp-file cleanup, even though the plan only intends to change enumeration failure handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Keep || true on the two while loops after reading the temp files; the separated if find branch still observes enumeration failure without changing loop-body failure behavior
  - From Codex-dyn-cleanup-fail-safe: Keep || true on the two read loops after redirecting from the temp files, so the if find branch owns only enumeration failure handling while loop-body failure handling stays unchanged

