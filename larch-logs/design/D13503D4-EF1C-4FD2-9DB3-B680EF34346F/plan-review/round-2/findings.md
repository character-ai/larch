### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/run-step3-review.sh:46-47
- **Concern**: Plan places --preview-only after argv/tmpdir/plugin-root resolution but does not relax or document the mandatory --round-cap check. Scenario: Uncaptured SKILL preview fence calling run-step3-review.sh --preview-only --design-tmpdir only exits 2 before any preview render; Step 3 loses the live plan header
- **Proposed resolution**: Either skip --round-cap validation when --preview-only and document that in run-step3-review.md, or pin the SKILL preview fence to pass --round-cap ${LARCH_DESIGN_ROUND_CAP:-5} alongside --preview-only

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:80-84
- **Concern**: Plan threads REPO into Step 3 pause guard(s) for assert_thin_fence but not which guard assert_thin_fence actually inspects. Scenario: assert_thin_fence selects the first pause-save line in the Step 3 region; that line is the timing-ledger fence (skills/design/SKILL.md:1023), not the new preview/review driver fences — updating only the latter leaves make lint failing until discovered manually
- **Proposed resolution**: Explicitly require ${REPO:+--repo "$REPO"} on the timing-ledger fence pause-save line (first guard in <!-- step:3 — … <!-- step:3.5), matching Step 3.6/3b entry-guard pinning

### FINDING_3:
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/run-step3-review.sh:46-55
- **Concern**: Preview-only mode is planned after existing review-path validation. Scenario: `--preview-only` can still fail on missing `--round-cap` or a failed `cd "$DESIGN_TMPDIR_ARG"` before it reaches the pure preview renderer
- **Proposed resolution**: Parse mode before validation; for `--preview-only` require only `--design-tmpdir`, pass the raw tmpdir to the renderer, and reserve `--round-cap` plus canonicalized tmpdir validation for `--no-preview` / review mode.

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/run-step3-review.sh:64-68
- **Concern**: Preview sentinel touch uses bare `[[ ! -s plan.txt ]]` as a stand-in for the documented empty-plan path. Scenario: After allowlist-invalid or missing/invalid tmpdir warnings the renderer exits before plan handling but `plan.txt` is often absent, so `! -s` is true and `--preview-only` can still touch `.step3-entry-plan-printed`; later valid Step 3 entry suppresses the preview permanently
- **Proposed resolution**: Touch only when renderer output contains `## Plan Candidate for Review` or the exact `plan.txt missing or empty` warning string; do not use filesystem `! -s` alone after allowlist/tmpdir failures (matches the planned disallowed-tmpdir no-sentinel harness case)

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/run-step3-review.sh:46-47
- **Concern**: Preview-only mode is planned as a separate SKILL fence but the plan does not relax or satisfy the existing --round-cap-required validation. Scenario: If --preview-only keeps the current required --round-cap check, the live preview fence exits 2 before rendering ## Plan Candidate for Review
- **Proposed resolution**: Update the plan so --preview-only either passes --round-cap in SKILL.md/tests or exempts --round-cap validation for preview-only mode

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1021-1025
- **Concern**: `assert_thin_fence` on Step 3 pins the first `design-pause-save` line in the region; that line is in the timing-ledger fence, not the new preview/review fences. Scenario: Plan threads `${REPO:+--repo "$REPO"}` into Step 3 pause guard(s) for thin-fence lint but does not call out the timing fence; `scripts/test-design-structure.sh` `assert_thin_fence` awk picks the first pause line before any `read-design-classification.sh` (absent in Step 3), so preview/review REPO alone leaves the checked guard without REPO and Step 3 `assert_thin_fence` fails
- **Proposed resolution**: Add `${REPO:+--repo "$REPO"}` to the timing-ledger fence pause-save at Step 3 entry (line ~1023), or extend `assert_thin_fence` with a Step-3-specific anchor on the `run-step3-review.sh --no-preview` fence; document which guard the harness pins

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/run-step3-review.sh:46-49
- **Concern**: Preview-only mode is specified after the existing required --round-cap validation. Scenario: The new live Step 3 fence may call --preview-only with only --design-tmpdir, but the driver exits 2 before rendering the preview, aborting the foreground SKILL fence under set -e
- **Proposed resolution**: Explicitly make --round-cap required only for --no-preview/review mode, or pass --round-cap in the preview-only SKILL fence and document that requirement

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1068-1080
- **Concern**: Thin-fence result-env read specifies only `! -L`, not the repo’s `[[ -f && ! -L ]]` pattern. Scenario: Missing `.step3-review-result.env` makes `[[ ! -L ]]` true; a `while read … done <file` under `set -e` can abort Step 3 before stdout KV fallback (common before the driver writes the env)
- **Proposed resolution**: Use `[[ -f "$DESIGN_TMPDIR/.step3-review-result.env" && ! -L "$DESIGN_TMPDIR/.step3-review-result.env" ]]` in SKILL.md, `apply_step3_handoff`, and matching structure pins

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/run-step3-review.sh:46-54
- **Concern**: Plan requires preview-only to emit missing or invalid tmpdir warnings, but places preview-mode handling after hard DESIGN_TMPDIR cd/pwd resolution. Scenario: `run-step3-review.sh --preview-only --design-tmpdir /missing` exits before invoking the renderer, so the warning-only preview contract is not preserved
- **Proposed resolution**: Handle preview-only invalid tmpdir before mandatory cd resolution, or narrow the plan to remove that warning-only acceptance criterion and test only existing valid/disallowed directories

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-sentinel-touch-conditions
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-run-step3-review.sh:167-182
- **Concern**: Planned harness updates omit a renderer-failure branch for sentinel touch. Scenario: The plan touches `.step3-entry-plan-printed` only when captured renderer stdout contains `## Plan Candidate for Review` or `[[ ! -s "$DESIGN_TMPDIR/plan.txt" ]]` (plan.txt lines 64-68), so a stub/bug that exits non-zero with non-empty stdout lacking the header must leave the sentinel absent and allow a later preview. Listed tests cover header touch, missing/empty `plan.txt`, and disallowed-tmpdir no-touch, but not non-zero junk stdout; an implementer could regress to touching on any non-empty `_preview_out` without a failing assertion
- **Proposed resolution**: Add one hermetic case via `RUN_STEP3_EMIT_PREVIEW_SH` that prints non-header body and exits 1; assert no `.step3-entry-plan-printed`, live output still emitted, and a second `--preview-only` run still renders the header and then creates the sentinel

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-sentinel-touch-conditions
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:59-68,167-180,281-296; skills/design/scripts/emit-design-plan-preview.sh:95-107
- **Concern**: Preview sentinel touch is underspecified for non-header renderer output, and planned tests do not include the requested unexpected non-empty non-header case. Scenario: The plan says to touch on header or bare `[[ ! -s "$DESIGN_TMPDIR/plan.txt" ]]`, but the renderer checks tmpdir validity before missing-plan handling. A disallowed tmpdir with no plan can make the bare missing-plan predicate true, and a renderer stub that exits non-zero with non-empty non-header output is not pinned by the planned `test-run-step3-review.sh` updates. Either case can over-touch `.step3-entry-plan-printed` and suppress a later valid preview.
- **Proposed resolution**: Tighten the plan so the missing-plan touch only fires after tmpdir validation succeeds or after the renderer emits the exact missing/empty-plan warning. Add one `RUN_STEP3_EMIT_PREVIEW_SH` stub test that prints non-empty non-header output, exits non-zero, and asserts no sentinel.

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-thin-fence-kv-ordering
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:127-129
- **Concern**: The Step 3 thin-fence bullets say "allowlisted KVs" but never list the keys (unlike `run-step3-review.md:35` and current `skills/design/SKILL.md:1075-1093`).. Scenario: An implementer could omit a key, add a spurious one, or drift from the driver contract; non-allowlisted `KEY=value` lines might be mis-handled relative to the display-echo path.
- **Proposed resolution**: In the `skills/design/SKILL.md` Step 3 fence bullet, pin the same 12 keys as today: `LOOP_STATUS`, `TALLY_PLAN_REVIEW_STATUS`, `STEP3_REVIEW_CAP_REACHED`, `STEP3_REVIEW_ROUND_NUM`, `ROUND_NUM`, `ACCEPTED_COUNT`, `IMPORTANT_ACCEPTED_COUNT`, `DEGRADED_PANEL`, `ROUNDS_COMPLETED`, `AGGREGATOR_STATUS`, `VOTING_TALLY_FILE`, `REVIEW_ROUND_COUNT` (plus `WARN` replay only).

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-thin-fence-kv-ordering
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:127-146; skills/design/scripts/run-step3-review.sh:268-293; skills/design/scripts/test-step3-orchestrator-fence.sh:60-82
- **Concern**: The plan says to parse allowlisted stdout KVs but never pins the stdout-fallback allowlist to the driver's outer result contract.. Scenario: An implementer could parse any KEY=value line, or omit a real terminal key. Then captured display or plan-like text such as LOOP_STATUS=complete can corrupt the Step 3 branch matrix, or a terminal key like STEP3_REVIEW_CAP_REACHED can be dropped.
- **Proposed resolution**: In the SKILL.md and test-step3-orchestrator-fence.sh plan bullets, state the exact stdout fallback allowlist: LOOP_STATUS, TALLY_PLAN_REVIEW_STATUS, STEP3_REVIEW_CAP_REACHED, STEP3_REVIEW_ROUND_NUM, ROUND_NUM, ACCEPTED_COUNT, IMPORTANT_ACCEPTED_COUNT, DEGRADED_PANEL, ROUNDS_COMPLETED, AGGREGATOR_STATUS, VOTING_TALLY_FILE, REVIEW_ROUND_COUNT; handle WARN as display-only. Require the later-KV-wins case to include an early plan-body-style allowlisted line plus a later terminal KV.
