Here is the normalized structured finding list (merged by shared risk/fix surface; reviewer slots preserved; out-of-scope kept separate with `[OUT_OF_SCOPE]` on the heading where applicable).

```text
### FINDING_1: CHANGELOG omits #2521 / NS_RETRY_REASON audit surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The changelog entry cites #2511 but not #2521 and does not document NS_RETRY_REASON in ns-retry `.meta`, reasons in ns-retry-sidecars NDJSON, or related audit/collector behavior that shipped on the same branch, so “what shipped” is incomplete for operators and tooling.
- **Suggested revision**: Add a Changed bullet with #2521 that describes NS_RETRY_REASON and ns-retry-sidecars reasons in NDJSON (aligned with what actually merged).

### FINDING_2: Duplicated `redact_gh_error` across gh helper scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The same `redact_gh_error` truncation / non-zero handling is copied across multiple scripts (`clarify-*`, `plan-block-*`, `tracking-issue-*`), so security posture, stderr messaging, and fail-closed behavior can drift with partial edits; generic error strings also differ between copies, weakening greps and runbooks.
- **Suggested revision**: Extract one sourced helper (or shared script) for `redact_gh_error`, use it everywhere, and unify the generic user-facing error string in one place.

### FINDING_3: No harness assertion for `reasons` in ns-retry-sidecars NDJSON
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Audit docs describe a `reasons` object in scan output, but the branch diff does not show an update to `test-audit-runs.sh` (or equivalent), so regressions could drop or malform `reasons` without CI catching it.
- **Suggested revision**: Add a fixture-level assertion that ns-retry-sidecars NDJSON includes a well-formed `reasons` field (shape/counts as intended).

### FINDING_4: Fragile NS_RETRY_REASON extraction and authority (append vs first match vs `=` in values)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Writes may append multiple `NS_RETRY_REASON=` lines while the audit scan effectively treats an early match as authoritative, so stale/duplicate lines mis-bin cause; parsing via `awk -F=` / “second field only” can truncate values if `=` appears inside the token/value.
- **Suggested revision**: Pick a single authority rule (last-wins scan or single canonical key rewrite on write) and parse by stripping the fixed `NS_RETRY_REASON=` prefix (or otherwise safely delimit), so audits reflect the intended final reason.

### FINDING_5: Plan vs harness naming drift (`C_NS_REASON` vs `C_NSR_REASON`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Checkpoint naming in plan text (`C_NS_REASON`) diverges from harness/comments (`C_NSR_*`), hurting traceability even without a functional gap.
- **Suggested revision**: Rename the harness label/comment to match the plan, or update the plan to the `C_NSR_*` convention—pick one canonical name.

### FINDING_6: [OUT_OF_SCOPE] `redact-tmpdir-paths` asymmetry vs `tracking-issue-write`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Some read-side gh stderr redaction paths still lack tmpdir-path redaction compared to `tracking-issue-write`, so tmpdir paths may remain in `ERROR=` after secret-only scrub; pre-existing asymmetry noted as follow-up material.
- **Suggested revision**: Align pipelines in a dedicated follow-up if policy requires parity.

### FINDING_7: [OUT_OF_SCOPE] Large `larch-logs/implement/**` commit footprint
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Large implement run-log footprint is intentional per repo run-log policy; not a defect for this feature review.
- **Suggested revision**: None required for this review scope.

### FINDING_8: `collect-agent-results.sh` can skip `NS_RETRY_META` / `NS_RETRY_REASON=` on early `continue` paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Structured NS retry paths that `continue` before meta annotation, or `preserve_and_publish_ns_retry` failures that `continue` early, can leave entries `NOT_SUBSTANTIVE` while ns-retry artifacts exist and without `NS_RETRY_REASON=`, causing UNKNOWN binning despite substantive retries.
- **Suggested revision**: Ensure meta annotation runs for these flows (reorder so `NS_RETRY_META` / reason write happens before `continue`, or add a single guaranteed exit path that always writes the canonical meta fields).

### FINDING_9: Non-deterministic key order in emitted `reasons` JSON
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `awk` associative-array iteration order can make NDJSON snapshots flap on key order only.
- **Suggested revision**: Sort reason keys before JSON emission (stable ordering for diffs/consumers).

### FINDING_10: Over-broad substring fail-closed match for `"[content truncated"` in gh error redaction
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: A substring match on a generic phrase could hypothetically over-scrub legitimate API text containing that substring into `unavailable`-style errors.
- **Suggested revision**: Narrow the sentinel match (or otherwise reduce false positives) if this risk matters for supported error shapes.

### FINDING_11: Unsafe interpolation of meta-derived reason strings into audit NDJSON JSON
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Reason strings from `.meta` are embedded into JSON without strict validation/escaping; crafted/corrupted values could break NDJSON lines or distort parser-visible structure despite assumptions about token charset.
- **Suggested revision**: Allowlist to safe tokens (map unknown to UNKNOWN) and/or build JSON with `jq` (or equivalent) so strings/keys are always JSON-safe.

### FINDING_12: [OUT_OF_SCOPE] Scrubber warnings hidden on `tracking-issue-read` redaction pipe
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Scrubber stderr is redirected to `/dev/null` on the read-side redaction pipeline, hiding `WARN` lines from `redact-secrets.sh`; observability gap largely predates the new stdout fail-closed behavior.
- **Suggested revision**: Optional follow-up: `tee`/log scrubber warnings without copying raw gh stderr into `ERROR=`.

### FINDING_13: [OUT_OF_SCOPE] Branch scope vs the five-file NS_RETRY_REASON plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Additional commits/paths beyond the narrow NS_RETRY_REASON plan (e.g., broader redaction/SECURITY/CHANGELOG/plugin.json/run logs) are noted as out of scope for reviewers targeting only #2521 plan fidelity.
- **Suggested revision**: None required for #2521 plan-fidelity review; scope reviewers accordingly.
```
