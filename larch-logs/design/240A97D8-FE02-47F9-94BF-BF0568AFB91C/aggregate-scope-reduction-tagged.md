### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/timing.py:21-45
- **Concern**: [SCOPE-REDUCTION] Retired sketch and dialectic task kinds remain allow-listed. Scenario: After deleting sketch and dialectic launch surfaces, timing still treats their task-kind slugs as first-class known design tasks, so hard-exclusive telemetry machinery remains instead of warning on stale callers.
- **Proposed resolution**: Add python/timing.py and matching timing tests to the plan; remove retired sketch, debate, and dialectic-judge task kinds that no surviving launcher emits.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/progress-reporting.md:156-172
- **Concern**: [SCOPE-REDUCTION] Shared progress examples still show design sketches and dialectic. Scenario: After the PR, shipped progress documentation would still teach users that /design has 2a sketches and 2a.5 dialectic, conflicting with the proposed one-flow design path.
- **Proposed resolution**: Add skills/shared/progress-reporting.md to the plan and rewrite the design examples to current one-flow step names with no 2a.5 dialectic breadcrumb.

### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: tests/fixtures/dialectic/README.md:1-35
- **Concern**: [SCOPE-REDUCTION] The plan deletes scripts/dialectic-smoke-test.sh and the protocol, but never deletes tests/fixtures/dialectic/. Scenario: The PR would leave HARD/dialectic-only test fixtures and stale references to the deleted smoke harness, which misses the issue requirement to remove machinery and tests exclusive to the removed flow.
- **Proposed resolution**: Add tests/fixtures/dialectic/ to the deletion surface, including its fixture subdirectories, after removing the smoke-test harness and all callers.

### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/write-design-round-meta.sh:285; skills/design/scripts/revise-plan-with-waterfall.sh:750-751; skills/design/scripts/test-plan-review-loop.sh:1959
- **Concern**: [SCOPE-REDUCTION] Cleanup grep includes generic TIER= and catches unrelated revise-tier metadata. Scenario: The plan's classification cleanup check would fail on REVISE_TIER outputs that are not design flow type, or push unnecessary renames outside the feature scope
- **Proposed resolution**: Narrow the cleanup check to actual pause/run-param tier fields, or remove TIER= from that broad grep and keep direct pause-save/load assertions that no TIER pause marker is emitted
