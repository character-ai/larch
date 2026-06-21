### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: manifest-schema-invalid recovery triggers false producer-missing warnings
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Manifest-schema-invalid recovery skips scout production, but Step 5 still reports `producer-missing` and logs a producer-failure warning. On Codex recovery runs, external scout sidecars are cleared, recovery commits without raw/normalized manifest, Step 5 sets `producer-missing`, appends Warnings, and final-summary shows static-only producer missing-or-invalid despite intentional plan exclusion of scout production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add recovery carve-out in review_pipeline/final_report or require recovery path to run normalize-coder-scout with intentional empty manifest before Step 3.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: design drafter missing-scout warning swallows run-log append failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Drafter missing-scout warning uses `run-log append-entry` with stdout/stderr redirected to `DEVNULL`. `run-log append` can fail while stderr still shows a warning; `final-summary` warning counts and `execution-issues.md` omit the event.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Remove DEVNULL redirects or check subprocess returncode and emit a loud failure like dispatch_panel producer-warning path.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: dispatch_panel trusts --pre-scouted-manifest without full Step 5 consumer contract
- **Reviewer(s)**: dyn-dyn-scout-gate-output.txt
- **Severity**: important
- **Concern**: `dispatch_panel` consumes `--pre-scouted-manifest` on `site == "implement Step 5"` without re-checking the full Step 5 consumer contract (`step2-external-scout-eligible.txt`, `SCOUT_CODER_STATUS=ok`, readable manifest). It only treats `producer_status` as invalid when the status env is truthy and not `ok`; empty/missing status is not invalid, so a caller passing `--pre-scouted-manifest` without the eligibility marker can still synthesize dynamic slots. `review_and_fix._preflight_step5` enforces the marker today, but the dispatch gate is the last line of defense against legacy `scout dynamic-archetypes` behavior and should not trust argv alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-scout-gate-output.txt: In the `scout_status == "na" and pre_scouted` branch, require `step2-external-scout-eligible.txt` plus `SCOUT_CODER_STATUS=ok` (or treat any other combination as `producer-invalid` with `scout_fail_reason=producer_sidecar_ineligible`) before calling `_normalize_scout_manifest`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: step-5-review.sh lacks mechanical normalize-coder-scout preflight
- **Reviewer(s)**: dyn-dyn-scout-gate-output.txt
- **Severity**: important
- **Concern**: The Step 5 launcher only execs `review-and-fix step5`; it does not mechanically verify or run `normalize-coder-scout` / `scout-coder-manifest.raw.json` materialization. Main-agent paths (`--emergency`, explicit `--coder claude`, tool-unavailable fallback) depend entirely on the orchestrator obeying the SKILL.md Step 2.4 fence. If that fence is skipped, Step 5 correctly avoids the legacy separate scout (`producer-missing` / static-only), but it also cannot recover coder-chosen dynamic archetypes in the same run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-scout-gate-output.txt: Add a lightweight preflight in `step-5-review.sh` or `review-and-fix step5` that checks for `step2-external-scout-eligible.txt` or runs `normalize-coder-scout` when a raw manifest exists, so emergency/main-agent runs get the same producer surface as Codex/Cursor without relying on prompt discipline alone.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_14: final_report returns unknown for legacy separate-scout SCOUT_STATUS=ok
- **Reviewer(s)**: dyn-dyn-summary-line-output.txt
- **Severity**: important
- **Concern**: When `step2-scout-coder-status.env` is absent and round 1 has `SCOUT_STATUS=ok` from the legacy separate scout (#4954 failure mode: `unknown/scout-round1-manifest.json.raw` in timing, no coder-produced sidecar), the function returns `unknown` because only `round_status == "pre-scouted"` is handled before the fallback. A run that actually launched dynamic reviewers via `scout dynamic-archetypes` is reported as `Dynamic archetypes: unknown`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-summary-line-output.txt: Treat round `SCOUT_STATUS=ok` like `pre-scouted`: read `round-*/scout-round*-manifest.json` and return `ok (N)` when the manifest is readable.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

