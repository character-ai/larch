### FINDING_1: Preview-only mode can fail before rendering
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Pragmatic, Codex-Edge, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: Preview-only handling is planned after existing review-mode validation/canonicalization, so a live Step 3 preview can exit before rendering due to missing `--round-cap`, failed tmpdir `cd`, or invalid/missing tmpdir handling that should instead produce preview warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Either skip --round-cap validation when --preview-only and document that in run-step3-review.md, or pin the SKILL preview fence to pass --round-cap ${LARCH_DESIGN_ROUND_CAP:-5} alongside --preview-only
  - From Codex-Arch, Codex-Pragmatic: Parse mode before validation; for `--preview-only` require only `--design-tmpdir`, pass the raw tmpdir to the renderer, and reserve `--round-cap` plus canonicalized tmpdir validation for `--no-preview` / review mode.
  - From Codex-Edge: Update the plan so --preview-only either passes --round-cap in SKILL.md/tests or exempts --round-cap validation for preview-only mode
  - From Codex-Innovation: Explicitly make --round-cap required only for --no-preview/review mode, or pass --round-cap in the preview-only SKILL fence and document that requirement
  - From Codex-Requirements: Handle preview-only invalid tmpdir before mandatory cd resolution, or narrow the plan to remove that warning-only acceptance criterion and test only existing valid/disallowed directories

### FINDING_2: Step 3 thin-fence REPO pin targets the timing-ledger fence
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The Step 3 `assert_thin_fence` guard inspects the first `design-pause-save` line in the Step 3 region, which is the timing-ledger fence rather than the new preview/review driver fences; updating only the latter leaves lint failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Explicitly require ${REPO:+--repo "$REPO"} on the timing-ledger fence pause-save line (first guard in <!-- step:3 — … <!-- step:3.5), matching Step 3.6/3b entry-guard pinning
  - From Cursor-Innovation: Add `${REPO:+--repo "$REPO"}` to the timing-ledger fence pause-save at Step 3 entry (line ~1023), or extend `assert_thin_fence` with a Step-3-specific anchor on the `run-step3-review.sh --no-preview` fence; document which guard the harness pins

### FINDING_3: Preview sentinel can be over-touched on failed or non-preview renderer output
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-sentinel-touch-conditions, Codex-dyn-sentinel-touch-conditions
- **Severity**: important
- **Concern**: The planned sentinel touch condition uses bare missing/empty `plan.txt` or insufficient output checks, so allowlist/tmpdir failures or non-header renderer output can still create `.step3-entry-plan-printed` and suppress a later valid preview; planned tests do not fully pin this failure branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Touch only when renderer output contains `## Plan Candidate for Review` or the exact `plan.txt missing or empty` warning string; do not use filesystem `! -s` alone after allowlist/tmpdir failures (matches the planned disallowed-tmpdir no-sentinel harness case)
  - From Cursor-dyn-sentinel-touch-conditions: Add one hermetic case via `RUN_STEP3_EMIT_PREVIEW_SH` that prints non-header body and exits 1; assert no `.step3-entry-plan-printed`, live output still emitted, and a second `--preview-only` run still renders the header and then creates the sentinel
  - From Codex-dyn-sentinel-touch-conditions: Tighten the plan so the missing-plan touch only fires after tmpdir validation succeeds or after the renderer emits the exact missing/empty-plan warning. Add one `RUN_STEP3_EMIT_PREVIEW_SH` stub test that prints non-empty non-header output, exits non-zero, and asserts no sentinel.

### FINDING_4: Result-env read guard treats a missing file as readable
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The Step 3 result-env read checks only `! -L`, so a missing `.step3-review-result.env` passes the guard and can abort the thin fence before stdout KV fallback under `set -e`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Use `[[ -f "$DESIGN_TMPDIR/.step3-review-result.env" && ! -L "$DESIGN_TMPDIR/.step3-review-result.env" ]]` in SKILL.md, `apply_step3_handoff`, and matching structure pins

### FINDING_5: Stdout KV fallback allowlist is underspecified
- **Reviewer(s)**: Cursor-dyn-thin-fence-kv-ordering, Codex-dyn-thin-fence-kv-ordering
- **Severity**: important
- **Concern**: The Step 3 thin-fence/stdout-fallback plan says to parse allowlisted KVs but does not pin the exact driver result contract, allowing implementers to parse arbitrary `KEY=value` text, omit terminal keys, or mishandle ordering between plan-body text and terminal KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-thin-fence-kv-ordering: In the `skills/design/SKILL.md` Step 3 fence bullet, pin the same 12 keys as today: `LOOP_STATUS`, `TALLY_PLAN_REVIEW_STATUS`, `STEP3_REVIEW_CAP_REACHED`, `STEP3_REVIEW_ROUND_NUM`, `ROUND_NUM`, `ACCEPTED_COUNT`, `IMPORTANT_ACCEPTED_COUNT`, `DEGRADED_PANEL`, `ROUNDS_COMPLETED`, `AGGREGATOR_STATUS`, `VOTING_TALLY_FILE`, `REVIEW_ROUND_COUNT` (plus `WARN` replay only).
  - From Codex-dyn-thin-fence-kv-ordering: In the SKILL.md and test-step3-orchestrator-fence.sh plan bullets, state the exact stdout fallback allowlist: LOOP_STATUS, TALLY_PLAN_REVIEW_STATUS, STEP3_REVIEW_CAP_REACHED, STEP3_REVIEW_ROUND_NUM, ROUND_NUM, ACCEPTED_COUNT, IMPORTANT_ACCEPTED_COUNT, DEGRADED_PANEL, ROUNDS_COMPLETED, AGGREGATOR_STATUS, VOTING_TALLY_FILE, REVIEW_ROUND_COUNT; handle WARN as display-only. Require the later-KV-wins case to include an early plan-body-style allowlisted line plus a later terminal KV.
