### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/scout-dynamic-archetypes.sh:297-322
- **Concern**: Waterfall treats any non-empty `${OUTPUT}.raw` as tier success before JSON validation. Scenario: Codex (or a harness `STUB_BIN/codex` writing `codex review`) exits 0 with non-JSON prose; scout never tries Claude and ends `SCOUT_STATUS=parse-failed` / zero archetypes despite Claude being available
- **Proposed resolution**: Define tier success as exit 0 plus post-`extract_valid_fenced_json`/`jq` parseability, or on parse-failed retry the next tier when `--codex-present true` and Claude not yet tried

### FINDING_2:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/scout-dynamic-archetypes.sh:12-14
- **Concern**: Waterfall stops at first tier with exit 0 and non-empty `${OUTPUT}.raw` before JSON validation. Scenario: `launch-review.sh` budget `cap_hit` writes non-empty `STATUS=cap_hit` to the output file and exits 0; `skills/review/scripts/test-dispatch-panel.sh` stub `codex` writes `codex review` prose when `--codex-available true` is forwarded as `--codex-present true`. Scout never runs the Claude tier, then parse/validation fails and yields zero archetypes despite a working Claude stub
- **Proposed resolution**: Define tier success as exit 0 plus parseable scout JSON (quick `jq`/`extract_valid_fenced_json` probe) or explicit launcher failure signals (`${raw}.cap-hit`, missing `${raw}.done` where applicable); on tier parse failure fall through to Claude. In `test-dispatch-panel.sh` dynamic cases stub `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH` or pass `--codex-present false` unless Codex JSON is stubbed

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/scout-dynamic-archetypes.sh:12-14
- **Concern**: Waterfall tier win is only exit 0 plus non-empty `${OUTPUT}.raw`. Scenario: `launch-review.sh` cap_hit and `test-dispatch-panel.sh` PATH `codex` stub both exit 0 with non-JSON in `.raw`, so Codex wins, Claude never runs, and scout ends `parse-failed`/empty archetypes; existing dynamic cases expect `SCOUT_STATUS=ok`
- **Proposed resolution**: Define tier failure as exit non-zero, empty raw, `${raw}.cap-hit` present, or raw not JSON-shaped (e.g. no `{`); only then run Claude; in `test-dispatch-panel.sh` stub `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH` to fail/empty for legacy dynamic scenarios or pass `--codex-present false` there

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-scout-dynamic-archetypes.sh:375-396
- **Concern**: Plan removes the 256 KB check from validate_context_input_file but only calls out a new >256 KB diff case; it does not revise the existing description-file oversize harness. Scenario: The harness at 375-396 still expects exit 2 and stderr contains exceeds 256 KB for a 270 KB --description-file; after the gate removal that case should succeed (with staging), so make lint fails unless the implementer discovers the conflict outside the plan
- **Proposed resolution**: In scripts/test-scout-dynamic-archetypes.sh testing strategy: replace the description-too-large failure assertions with a success path (staged path in prompt, SCOUT_STATUS ok or empty per stub) or drop the case if redundant with the new large diff assertion; state this explicitly beside the >256 KB diff harness bullet

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-override-variable-isolation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:17; <TMPDIR>/plan.txt:43; scripts/test-scout-dynamic-archetypes.sh:375-396
- **Concern**: Plan removes the 256 KB gate from validate_context_input_file for all bulk context files but the harness update only calls out a large diff case. Scenario: The existing description-too-large case still expects exit 2 and stderr contains exceeds 256 KB; after the gate is removed that assertion fails even though the new diff-size behavior is correct
- **Proposed resolution**: Explicitly retarget or remove scripts/test-scout-dynamic-archetypes.sh:375-396 (e.g. assert a >256 KB --description-file is accepted/staged, or keep a separate inline --description-text argv cap test only)
