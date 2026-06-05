### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: correctness
- **Location**: plan.txt:57-59
- **Concern**: `scripts/larch-log.md` step still tells implementers to conditionally sync `scripts/test-lib-design-round-artifacts.md`, which is not in the repo. Scenario: Accepted plan-review FINDING_4 asked to drop the ghost doc reference; implementers may search for a missing file or treat the step as blocking
- **Proposed resolution**: Reword the `scripts/larch-log.md` bullet to name only existing companions (`scripts/lib-design-round-artifacts.md`, `scripts/test-lib-design-round-artifacts.sh`); keep `scripts/test-larch-log-write-round.md` unconditional per FINDING_3

### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/lib-design-round-artifacts.sh:8; scripts/test-lib-design-round-artifacts.sh:40-45
- **Concern**: The plan adds design plan-review artifact allowlist changes that are unrelated to the feature description's implement-log Dynamic Codex inclusion contract.. Scenario: This SIMPLE lane PR would expand from implement run-log contract/tests into design snapshot behavior and extra docs/tests, increasing review surface without being required for the stated issue.
- **Proposed resolution**: Remove the design artifact updates from this plan and handle that producer-name correction in a separate focused issue/PR unless it is proven necessary for the Dynamic Codex implement-log fix.

### FINDING_3:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-larch-log-write-round.sh:50-55
- **Concern**: The plan says to keep existing static Codex exclusion assertions, but the current harness only creates/asserts the unphased static Codex .meta sidecar and not the raw codex-specialist-*-output.txt named in the feature description.. Scenario: The stated static-vs-dynamic boundary could regress for raw static Codex transcripts while the proposed tests still pass.
- **Proposed resolution**: Add a raw codex-specialist-security-output.txt fixture and assert it is excluded alongside the dynamic Codex inclusion assertions.

### FINDING_4:
- **Reviewer(s)**: Codex-dyn-fixture-producer-name
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/dispatch-panel.sh:202-206, scripts/dispatch-with-waterfall.sh:183-199,456-461, scripts/launch-review.sh:547-550
- **Concern**: The planned `dyn-api-contract-codex-output-phase2.txt.events.jsonl` fixture is not traceable to a real producer. Dynamic Codex slots use base `dyn-<name>-codex-output.txt`; phase2 runs `other_tool codex` = Cursor and only Codex launches write `${OUTPUT}.events.jsonl`.. Scenario: The SIMPLE regression suite would encode a fictional phased dynamic-Codex events sidecar and expand the contract beyond real artifacts.
- **Proposed resolution**: Drop the `dyn-api-contract-codex-output-phase2.txt.events.jsonl` fixture/assertion; keep the real unphased Codex `.events.jsonl` negative coverage.
