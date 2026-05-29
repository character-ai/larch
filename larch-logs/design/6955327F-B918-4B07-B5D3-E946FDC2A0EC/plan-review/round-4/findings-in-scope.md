Verifying the cited code paths so we can normalize findings and decide whether FINDING_1 and FINDING_2 should merge.
Three distinct correctness issues around scout cap-hit handling and test contracts; FINDING_1 and FINDING_2 are related but need different fixes, so they stay separate.

### FINDING_1: Stale cap-hit sidecar after tier waterfall
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: After a Codex tier hits the token budget, `launch-review.sh` writes `STATUS=cap_hit` to `${OUTPUT}.raw` and creates `${OUTPUT}.raw.cap-hit`, then exits 0. If the waterfall reuses the same raw path for Claude without removing the sidecar, `tier_raw_is_scout_json` can treat a present `.cap-hit` as a tier miss even after Claude overwrites `${OUTPUT}.raw` with valid JSON. A successful Claude response can be misclassified and yield `SCOUT_STATUS=empty` instead of `ok`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: In the waterfall loop, rm -f "${tier_raw}.cap-hit" immediately before each tier launch (or use per-tier raw paths). Document the cleanup in scout-dynamic-archetypes.md.

### FINDING_2: cap-hit probe uses wrong sibling path
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: If `tier_raw_is_scout_json` checks `${raw_path%.raw}.cap-hit` while scout passes `--output "${OUTPUT}.raw"` to `launch-review.sh`, the sidecar is written at `${OUTPUT}.raw.cap-hit` (see `launch-review.sh` line 186: `${OUTPUT}.cap-hit` relative to the output path). Stripping `.raw` makes the probe look for `${OUTPUT}.cap-hit`, so budget-capped tiers may not register as probe misses and Codex prose can win or fall through unpredictably.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `tier_raw_is_scout_json`, test only `[[ -f "${raw_path}.cap-hit" ]]` (or equivalent) using the same `--output` path passed to launch-review; drop the `%.raw` variant from the plan/helper spec

### FINDING_3: Plan test tokens mismatch production SCOUT_FAIL_REASON
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: A planned testing section names `SCOUT_FAIL_REASON` tokens that do not match production. Current scout emits `json_parse`, `invalid_archetypes_shape`, `validation_jq_error`, and `fence_strip_io` (see `scripts/scout-dynamic-archetypes.sh` and `scripts/test-scout-dynamic-archetypes.sh`). Plan literals such as `missing-raw`, `malformed`, `invalid-shape`, and `validation-jq-error` would cause new assertions to grep the wrong strings or pressure a token rename, regressing the existing single-tier parse-failed contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Keep existing `SCOUT_FAIL_REASON` values unchanged; map plan test bullets to current tokens (e.g. missing-raw case → `json_parse`, invalid-shape → `invalid_archetypes_shape`)
