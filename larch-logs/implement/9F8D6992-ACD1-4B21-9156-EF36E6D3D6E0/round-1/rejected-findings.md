### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Metadata-only warnings can reject successful probes
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Gate detection runs before `rc == 0` success handling, so a successful probe emitting only a model-metadata warning can be classified as failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Require non-zero exit or the server "requires a newer version of Codex" line before classifying metadata-only warnings as a CLI gate.
  - From cursor-specialist-edge-cases: Only classify model-metadata-not-found as a hard gate when rc!=0, or require both metadata and newer-Codex server signals at probe time.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Gate-detail TTL rules are inconsistent
- **Reviewer(s)**: dyn-dyn-probe-cache
- **Severity**: minor
- **Concern**: Cached-negative reload and `_current_codex_gate_detail()` use different maximum-age formulas, so status and reviewer results can disagree about whether the same gate-detail record is valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-probe-cache: Use one shared helper for gate-detail max age in both call sites (same formula everywhere), or store an explicit expiry in the handoff JSON and reject expired records in both readers.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Cached negative probes can preserve stale gate state
- **Reviewer(s)**: dyn-dyn-probe-cache
- **Severity**: major
- **Concern**: A cached negative probe suppresses re-execution after Codex is upgraded, continuing to report `codex_present=false` and stale upgrade guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-probe-cache: On a cached negative hit, either re-run a lightweight live probe before surfacing gate detail, or key gate-detail validity to the same negative stamp mtime and refuse upgrade advice once the stamp outlives a fresh probe (clear detail when serving a cache hit if the handoff record is older than the stamp).


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Degraded-tools output drops in-process gate detail
- **Reviewer(s)**: dyn-dyn-probe-cache
- **Severity**: minor
- **Concern**: `degraded_tools_result()` only reloads gate detail from disk, so a handoff write failure causes Step 0 to lose actionable upgrade guidance even though `check_reviewers()` already has the detail in memory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-probe-cache: Thread optional gate detail from `check_reviewers()` into `degraded_tools_result()` / `degraded_tools_gate_main()` (disk read as fallback only), mirroring the status path.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_10: Gate-detail substitution lacks regression coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The actionable degraded-tools explanation may regress to the generic probe-failed message without a CI test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Test degraded_tools_result/degraded_tools_gate_main explanation contains actionable upgrade text when gate detail exists


Vote tally: YES=1 NO=2 JUDGE_ERROR=0
