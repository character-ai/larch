### FINDING_1:
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:84-86,99-100,44
- **Concern**: Conflicting terminal status when every tier misses the JSON probe. Scenario: Testing strategy requires fail-open (`{"archetypes":[]}`) when all tiers fail launch or JSON probe, while Edge cases require `SCOUT_STATUS=parse-failed` when the last tier’s raw fails the probe; the plan also says existing malformed/missing-raw harness assertions still pass (parse-failed today). A single-tier Claude run with exit-0 non-JSON (e.g. `scripts/test-scout-dynamic-archetypes.sh` missing-raw/malformed cases) cannot satisfy both.
- **Proposed resolution**: Pick one contract and align Edge cases, Testing strategy, and harness retarget list: either keep today’s parse-failed for any exit-0 raw that fails the probe (and change line 44 to “fail-open only when every tier fails launch/timeout/empty raw”), or adopt fail-open for exhausted probe misses and retarget missing-raw/malformed/invalid-shape expectations explicitly.

### FINDING_2:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:84-86;plan.txt:44;plan.txt:99-100
- **Concern**: Edge cases require parse-failed when the last tier’s raw fails the JSON probe, but Testing strategy and Failure modes require fail-open when all tiers fail launch or JSON probe. Scenario: With Codex then Claude both returning unparseable raw, an implementer following Edge cases calls emit_parse_failed_result and breaks test-dispatch-panel/dynamic-parse-failed expectations and the stated fail-open contract; following Testing strategy contradicts Edge cases
- **Proposed resolution**: Make multi-tier exhaustion explicit: no winner after the loop → write_empty_manifest plus a non-parse-failed SCOUT_STATUS (e.g. empty or claude-failed); reserve emit_parse_failed_result for single-tier Claude-only probe failure only; delete or rewrite Edge cases lines 85-86 to match
