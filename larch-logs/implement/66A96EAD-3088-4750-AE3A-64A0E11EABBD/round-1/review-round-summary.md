# Review Round 1

- Mode: `diff`
- 7 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_2: Step 5 `_normalize_scout_manifest` silently empties non-empty producer manifests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-dyn-scout-gate-output.txt
- **Severity**: important
- **Concern**: `_normalize_scout_manifest` drops invalid entries but returns `True`, so a non-empty producer manifest (e.g. float `weight` 1.0 passing `filter-manifest` but failing `_valid_dynamic_archetype` int check) can be classified as `pre-scouted-empty` instead of `producer-invalid`. Dynamic slots become zero without a producer-failure warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Treat raw-nonempty-but-normalized-empty as producer-invalid on implement Step 5, or reuse filter-manifest for Step 5 pre-scouted normalization.
  - From cursor-specialist-edge-cases-output.txt: Treat input-nonempty/output-empty after normalization as producer-invalid; or compare against raw archetype count from Step 2 sidecar.
  - From dyn-dyn-scout-gate-output.txt: After normalization, compare raw archetype count from `--pre-scouted-manifest` (or re-run `scout filter-manifest --mode review`) against filtered count; if raw > 0 and filtered == 0 on implement site, set `producer-invalid` with fail reason `pre_scouted_filtered_to_zero` instead of `pre-scouted-empty`.


### FINDING_4: Missing `test_implement_dispatch` coverage for claude_fallback scout cleanup
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test verifies that `_clear_external_scout_state` removes new scout sidecars (`step2-scout-coder-status.env`, `scout-coder-manifest.raw.json`, etc.) on `claude_fallback`. Stale `SCOUT_CODER_STATUS=ok` could leak across tmpdir reuse or fallback without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the missing test_implement_dispatch cases from the plan.
  - From cursor-specialist-testing-output.txt: Add test_implement_dispatch coverage: seed scout sidecars, trigger claude_fallback dispatch, assert normalized manifest marker status env raw json and outdir copies are all removed.


### FINDING_6: Producer-scout warning sentinel written even when run-log append fails
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `.producer-scout-warning-logged` is written even when `run-log append-entry` fails. A failed append leaves stderr diagnostics only, blocks later retries, and leaves `execution-issues.md` and final warning counts wrong.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Write .producer-scout-warning-logged only on append success; allow retry or record append-failed separately.


### FINDING_7: `final_report` returns `unknown` before reading round scout status
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, dyn-dyn-summary-line-output.txt
- **Severity**: important
- **Concern**: `_dynamic_archetypes_line` returns `"unknown"` as soon as `step2-scout-coder-status.env` is missing, before `_first_round_scout_status` reads `round-*/scout-round*-status.env`. When the main-agent normalize fence is skipped (`/implement --emergency`), Step 5 still records `producer-missing`, `producer-invalid`, or `skipped-*` in round status, but the final summary shows `Dynamic archetypes: unknown` instead of the planned diagnostic lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Read first-round scout status before the missing status-file return, and prioritize producer-missing, producer-invalid, and skipped-* statuses.
  - From dyn-dyn-summary-line-output.txt: Read `_first_round_scout_status` before the early return (or only return `"unknown"` when both the Step 2 sidecar and round scout status are absent). Prefer round status for `producer-*` and `skipped-*` even when the Step 2 file is missing.


### FINDING_8: Cached round scout manifest can bypass implement Step 5 producer gate
- **Reviewer(s)**: dyn-dyn-scout-gate-output.txt
- **Severity**: important
- **Concern**: On `site == "implement Step 5"`, when `--pre-scouted-manifest` is absent and the producer sidecar is missing/invalid, dispatch still checks for a cached `scout-round{N}-manifest.json` plus `SCOUT_STATUS=ok` before the implement-only gate at 1088-1101. A reused `round-N/` directory from an earlier run can re-synthesize dynamic reviewer slots without a coder-produced manifest and without hitting `producer-missing` / `producer-invalid`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-scout-gate-output.txt: In the `elif scout_status == "na"` cached-manifest branch, short-circuit when `site == "implement Step 5"` and `--pre-scouted-manifest` is empty: skip the `SCOUT_STATUS=ok` reuse path and fall through to the implement producer gate (or require an eligible `step2-external-scout-eligible.txt` + `SCOUT_CODER_STATUS=ok` before reusing any round-local scout artifact).


### FINDING_9: `.producer-scout-warning-logged` not cleared on claude_fallback scout reset
- **Reviewer(s)**: dyn-dyn-scout-gate-output.txt
- **Severity**: important
- **Concern**: `_clear_external_scout_state()` clears coder scout sidecars on `claude_fallback` but does not remove `$IMPLEMENT_TMPDIR/.producer-scout-warning-logged`. A fallback/retry in the same session can leave the sentinel from an earlier producer failure, so `_append_producer_scout_warning_once()` skips the persisted `Warnings` bullet even though scout state was reset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-scout-gate-output.txt: Unlink `.producer-scout-warning-logged` inside `_clear_external_scout_state()`, or reset it whenever `step2-scout-coder-status.env` is rewritten to a non-ok status.


### FINDING_10: `final_report` dynamic count sourced from Step 2 manifest instead of round manifest
- **Reviewer(s)**: dyn-dyn-summary-line-output.txt
- **Severity**: important
- **Concern**: For successful dynamic paths, `ok (N)` counts archetypes in root `scout-coder-manifest.json`, not `round-1/scout-round1-manifest.json`, which Step 5 actually consumes after `_normalize_scout_manifest`. The second pass can drop entries that survived `filter-manifest`, so the summary can overstate how many dynamic reviewers ran.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-summary-line-output.txt: When round status is `pre-scouted` and `round-1/scout-round1-manifest.json` exists, derive `N` from that file (fall back to the Step 2 manifest only when the round file is absent).


