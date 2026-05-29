### FINDING_1:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/scout-dynamic-archetypes.sh:14-21; scripts/launch-review.sh:185-186
- **Concern**: Stale ${OUTPUT}.raw.cap-hit after a Codex cap_hit is not cleared before the Claude tier. Scenario: Codex budget cap writes STATUS=cap_hit to ${OUTPUT}.raw and creates ${OUTPUT}.raw.cap-hit, then exits 0. tier_raw_is_scout_json treats a present .cap-hit as a tier miss, but the sidecar is left on disk when Claude overwrites ${OUTPUT}.raw. A valid Claude JSON response can still fail the probe and yield SCOUT_STATUS=empty instead of ok.
- **Proposed resolution**: In the waterfall loop, rm -f "${tier_raw}.cap-hit" immediately before each tier launch (or use per-tier raw paths). Document the cleanup in scout-dynamic-archetypes.md.

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/scout-dynamic-archetypes.sh (plan ~line 21)
- **Concern**: tier_raw_is_scout_json lists `${raw_path%.raw}.cap-hit` as a cap-hit sibling. Scenario: Scout passes `--output "${OUTPUT}.raw"` to launch-review.sh; launch-review writes cap-hit at `${OUTPUT}.raw.cap-hit` (scripts/launch-review.sh:186). Stripping `.raw` looks for `${OUTPUT}.cap-hit`, so budget-cap tiers may not be treated as probe misses and Codex prose can win or fall through unpredictably
- **Proposed resolution**: In `tier_raw_is_scout_json`, test only `[[ -f "${raw_path}.cap-hit" ]]` (or equivalent) using the same `--output` path passed to launch-review; drop the `%.raw` variant from the plan/helper spec

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-scout-dynamic-archetypes.sh (plan ~line 46)
- **Concern**: Testing section names SCOUT_FAIL_REASON tokens that do not exist. Scenario: Current scout emits `json_parse`, `invalid_archetypes_shape`, `validation_jq_error`, and `fence_strip_io` (scripts/scout-dynamic-archetypes.sh:343-422; harness at test lines 197/228/236/246). Plan cites `missing-raw`, `malformed`, `invalid-shape`, and `validation-jq-error` as token literals
- **Proposed resolution**: New assertions may grep the wrong strings or change production tokens; single-tier parse-failed contract regresses Keep existing `SCOUT_FAIL_REASON` values unchanged; map plan test bullets to current tokens (e.g. missing-raw case → `json_parse`, invalid-shape → `invalid_archetypes_shape`)
