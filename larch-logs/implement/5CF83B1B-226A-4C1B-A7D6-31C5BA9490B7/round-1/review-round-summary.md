# Review Round 1

- Mode: `diff`
- 9 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Recompute and validate terminal identity after waits
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: major
- **Concern**: Terminal validation relies on launch identity computed before a blocking wait. If materialization, handoff, HEAD_SHA, BASE_REF, or DIFF_FINGERPRINT changes while waiting or between retry attempts, stale child results may be accepted or the retry may use the wrong identity. Recompute the current identity immediately before terminal handling, reject drift, clear stale state, and start a fresh attempt 1 without consuming the attempt-2 budget.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Add harness case mutating materialize env tuple fields and asserting fresh launch with recomputed fingerprint
  - From cursor-specialist-testing: Stub attempt-1 failure change handoff or materialization and assert fresh attempt-1 for new identity


### FINDING_2: Correctly classify missing terminal identity during failed attempts
- **Reviewer(s)**: dyn-dyn-bgjob-identity
- **Severity**: major
- **Concern**: `handle_terminal_outcome` treats missing terminal assessment identity as input drift before considering retryability. A child crash, orphan, or pre-`write_result` death can therefore reset to attempt 1 repeatedly instead of following the contracted attempt-2 retry/fail-closed path. Distinguish missing identity from non-empty identity drift; when launch identity is established and the terminal attempt is 1 or empty, route to retry or attempt-2 fail-closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-identity: Distinguish “missing terminal identity” from “identity drift.” When launch identity was already established and `TERM_ATTEMPT` is `1` or empty, route to `retry` (or straight to attempt-2 `fail-closed` preseed) even if assessment KVs are absent; reserve `fresh-identity` for cases where terminal KVs are present and differ from the freshly computed launch identity.


### FINDING_3: Revalidate completed rejoin results after waiting
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: Completed rejoin can emit success from stale `result.env` without checking the return status and `BGJOB_STATUS` from `wait_probe_zero`, or re-running terminal success/fail-closed validation after the wait. A failed or dead wait can therefore produce `ASSESSMENT_STATUS=complete` with incomplete or stale data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_4: Require the complete terminal envelope, including BGJOB_RC
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness
- **Severity**: major
- **Concern**: Terminal success and fail-closed validation omit required fields. In particular, `ASSESSMENT_ATTEMPT` and `BGJOB_RC` may be absent while the envelope is accepted. Require the full required KV set; for fail-closed envelopes require a non-empty non-zero `BGJOB_RC`; reject malformed or incomplete envelopes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.


### FINDING_5: Validate child stdout as an exact unique KV envelope
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-testing
- **Severity**: major
- **Concern**: Child stdout accepts valid-looking records while ignoring malformed, unknown, duplicate, invalid, or incomplete records. This violates the exact `KEY=value` contract and can allow a plausible successful assessment to be emitted from ambiguous output. Validate every line against an allowlist, reject malformed or duplicate keys and invalid values, and require exactly one occurrence of every required key; add corresponding harness coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-testing: Reject unknown and malformed lines and require exactly one occurrence of each required stdout key; add corresponding harness cases.


### FINDING_7: Contain and revalidate child merge-result paths
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Child-supplied merge-result paths are not sufficiently confined to `IMPLEMENT_TMPDIR` or behaviorally covered by tests. An outside regular file may be overwritten, and symlinks or non-regular files may be mishandled. Canonicalize and containment-check the path and parents, reject symlinks and non-regular files, recheck before replacement, and add negative tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Canonicalize and containment-check the path and parents, reject symlinks and non-regular files, and recheck before replacement.
  - From codex-specialist-testing: Add behavioral symlink/non-regular-file cases for every protected path and exercise reserved-key rejection through child writes.


### FINDING_8: Fail closed when stale-state cleanup fails
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Cleanup failures are ignored. Stale result files or registry rows can remain and be consumed as current on a later invocation. Fail closed on cleanup errors and verify targets are absent before launching fresh work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_9: Keep live rejoin identity handling safe when merge.env is incomplete
- **Reviewer(s)**: dyn-dyn-bgjob-identity
- **Severity**: major
- **Concern**: For a live registry row, missing or unreadable `merge.env` is treated as an identity mismatch because empty identity fields fail comparison. This can block safe rejoin and emit the wrong error class. Use merge identity when complete, otherwise use a validated fallback such as result identity or emit a distinct missing-identity failure; only report identity mismatch when a non-empty stored identity differs from the current identity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-identity: For `REGISTRY_STATE=live`, derive launch identity from merge env when complete, else fall back to the result env (or fail closed with a distinct error such as `missing-launch-identity`), and emit `active-stale-identity-mismatch` only when a non-empty stored identity differs from the current launch identity.


### FINDING_12: Add missing stale-input and retry-drift harness cases
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-bgjob-identity
- **Severity**: minor
- **Concern**: The harness does not cover all required stale-input and failure-recovery paths, including changed HEAD_SHA/BASE_REF/DIFF_FINGERPRINT, attempt-1 failure followed by identity drift, and a live rejoin whose wait returns `DEAD` without a result envelope. These gaps could mask stale acceptance or incorrect retry budgeting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add harness case mutating materialize env tuple fields and asserting fresh launch with recomputed fingerprint
  - From cursor-specialist-testing: Stub attempt-1 failure change handoff or materialization and assert fresh attempt-1 for new identity
  - From dyn-dyn-bgjob-identity: The harness covers live rejoin when the result env carries matching assessment identity (e.g. `incomplete` + timeout), but not live rejoin when `bgjob wait --max-wait-s 0` returns `DEAD` with no result env. That gap would have masked the `fresh-identity` misroute above.
