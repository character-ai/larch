### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-larch-log-write-round.sh:110-146
- **Concern**: Plan adds an explicit dyn-Codex allow arm but no negative fixture for dyn-Codex prompt sidecars. Scenario: Plan Failure modes claim existing and new assertions pin `.prompt` exclusion after the new allow; harness only asserts prompt exclusion for `codex-specialist-*` (lines 113-114, 143-144), not `dyn-*-codex-output*.prompt`. A case-order regression that places the allow before the `*-output*.prompt` deny could commit launcher prompts without CI failure
- **Proposed resolution**: Add `dyn-api-contract-codex-output.txt.prompt` (and phased twin) to fixtures with `assert_not_file` mirroring the static Codex prompt checks

### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-larch-log-write-round.sh:71-88
- **Concern**: Dynamic Codex .cap-hit sidecars are part of the proposed allow contract but the test plan only adds phased .meta/.json coverage. Scenario: An implementation can omit dyn-*-codex-output-*.txt.cap-hit or unphased .cap-hit from the explicit allow clause and still pass the planned regression tests, dropping cap-hit forensic sidecars despite the stated acceptance criterion
- **Proposed resolution**: Add a minimal .cap-hit fixture/assertion for the phased dynamic Codex case, and include unphased coverage too if no existing assertion covers it

### FINDING_3:
- **Reviewer(s)**: Codex-dyn-artifact-taxonomy
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:181-226; scripts/design-log-publish.sh:303-305,386-403; scripts/lib-design-round-artifacts.md:21-27
- **Concern**: 1. Proposed design-log policy comment overstates the actual artifact boundary. Scenario: The plan says to restate a design-log policy that excludes all raw reviewer outputs, but producers write cursor-plan-* and codex-primary-plan-* outputs at DESIGN_TMPDIR root, and design-log-publish stages top-level files by default except suffix scratch patterns. The planned comment would contradict the actual publisher contract and could drive unnecessary top-level deny-list scope creep.
- **Proposed resolution**: Narrow the new comment/doc text to say plan-review/round-N excludes raw reviewer outputs and findings.md is canonical for that round snapshot. Do not claim all design-log raw reviewer outputs are excluded unless the plan also intentionally changes design-log-publish and its tests.

### FINDING_4:
- **Reviewer(s)**: Codex-dyn-sidecar-boundary
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/design-log-publish.sh:294-309,388-403; skills/design/scripts/dispatch-plan-review-panel.sh:181-198,214-228
- **Concern**: The design-log fix only updates the plan-review round allowlist, but design-log-publish still stages every top-level design tmpdir file except suffix-denied sidecars; plan-review dispatch writes raw Cursor/Codex outputs at that top level.. Scenario: After the PR, codex-primary-plan-*-output.txt and cursor-plan-*-output.txt remain publishable at larch-logs/design/<run-id>/ even though the plan says raw reviewer outputs are excluded and findings.md is canonical.
- **Proposed resolution**: Either scope the plan wording to plan-review/round-N only, or add the real raw output patterns to design_artifact_excluded and pin them in scripts/test-design-log-publish.sh.

### FINDING_5:
- **Reviewer(s)**: Codex-dyn-fixture-reality
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/larch-log.sh:67-96; scripts/test-larch-log-write-round.sh:71-128
- **Concern**: Finding 1: Proposed dyn-Codex allow is a no-op and the new assertions would still pass through the existing broad output allow. Scenario: The planned dyn-api-contract-codex-output-phase2.txt fixture is a real producer shape, via skills/review/scripts/dispatch-panel.sh:202-210 plus scripts/dispatch-with-waterfall.sh:191-199, but scripts/larch-log.sh:95 already includes *-output-*.txt and sidecars after the static Codex deny at scripts/larch-log.sh:77-79. The new runtime branch adds ordering-sensitive complexity without changing or test-isolating behavior.
- **Proposed resolution**: For SIMPLE scope, drop the larch-log.sh allow-clause change. Keep the phased fixture assertions as regression coverage, and if needed add only a comment/doc clarification near the existing broad allow.
