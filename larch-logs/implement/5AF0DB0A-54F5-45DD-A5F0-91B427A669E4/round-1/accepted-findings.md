### FINDING_1: CHANGELOG omits #2521 / NS_RETRY_REASON audit surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The changelog entry cites #2511 but not #2521 and does not document NS_RETRY_REASON in ns-retry `.meta`, reasons in ns-retry-sidecars NDJSON, or related audit/collector behavior that shipped on the same branch, so “what shipped” is incomplete for operators and tooling.
- **Suggested revision**: Add a Changed bullet with #2521 that describes NS_RETRY_REASON and ns-retry-sidecars reasons in NDJSON (aligned with what actually merged).


### FINDING_11: Unsafe interpolation of meta-derived reason strings into audit NDJSON JSON
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Reason strings from `.meta` are embedded into JSON without strict validation/escaping; crafted/corrupted values could break NDJSON lines or distort parser-visible structure despite assumptions about token charset.
- **Suggested revision**: Allowlist to safe tokens (map unknown to UNKNOWN) and/or build JSON with `jq` (or equivalent) so strings/keys are always JSON-safe.


### FINDING_3: No harness assertion for `reasons` in ns-retry-sidecars NDJSON
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Audit docs describe a `reasons` object in scan output, but the branch diff does not show an update to `test-audit-runs.sh` (or equivalent), so regressions could drop or malform `reasons` without CI catching it.
- **Suggested revision**: Add a fixture-level assertion that ns-retry-sidecars NDJSON includes a well-formed `reasons` field (shape/counts as intended).


### FINDING_4: Fragile NS_RETRY_REASON extraction and authority (append vs first match vs `=` in values)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Writes may append multiple `NS_RETRY_REASON=` lines while the audit scan effectively treats an early match as authoritative, so stale/duplicate lines mis-bin cause; parsing via `awk -F=` / “second field only” can truncate values if `=` appears inside the token/value.
- **Suggested revision**: Pick a single authority rule (last-wins scan or single canonical key rewrite on write) and parse by stripping the fixed `NS_RETRY_REASON=` prefix (or otherwise safely delimit), so audits reflect the intended final reason.


### FINDING_8: `collect-agent-results.sh` can skip `NS_RETRY_META` / `NS_RETRY_REASON=` on early `continue` paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Structured NS retry paths that `continue` before meta annotation, or `preserve_and_publish_ns_retry` failures that `continue` early, can leave entries `NOT_SUBSTANTIVE` while ns-retry artifacts exist and without `NS_RETRY_REASON=`, causing UNKNOWN binning despite substantive retries.
- **Suggested revision**: Ensure meta annotation runs for these flows (reorder so `NS_RETRY_META` / reason write happens before `continue`, or add a single guaranteed exit path that always writes the canonical meta fields).


### FINDING_9: Non-deterministic key order in emitted `reasons` JSON
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `awk` associative-array iteration order can make NDJSON snapshots flap on key order only.
- **Suggested revision**: Sort reason keys before JSON emission (stable ordering for diffs/consumers).


