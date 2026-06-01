### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1299-1306
- **Concern**: Plan driver pseudocode omits stdout capture for emit_kv helpers (`design-log-publish.sh`, `upsert-diagrams-comment.sh`). Scenario: `PUBLISH_OK` / `UPSERT_STATUS` / `ARCHITECTURE_SOURCE` are emitted on stdout; item 9 only redirects stderr to `design-log-publish.failure.log` and item 7 has no `_upsert_out=$(…)` — parsing never runs, so rename gating (`PUBLISH_OK=true`) and the `⏩ 5c.5` status line drift from today’s SKILL behavior
- **Proposed resolution**: Mirror `design-route.sh` / current Step 5c item 9: `set +e; _publish_out=$("$PLUGIN_ROOT/scripts/design-log-publish.sh" … 2> "$DESIGN_TMPDIR/design-log-publish.failure.log"); _publish_rc=$?; set -e` then parse `_publish_out`; for upsert `set +e; _upsert_out=$("$PLUGIN_ROOT/scripts/upsert-diagrams-comment.sh" …); _upsert_rc=$?; set -e` then parse `_upsert_out` (optionally keep `diagrams-architecture-upsert.{stdout,stderr}` captures); preserve the `_publish_rc` non-zero && no `PUBLISH_OK=` unexpected-failure branch from `skills/design/SKILL.md:1305`

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/render-final-summary.sh:9-10,58-67,491-505
- **Concern**: Planned design-publish.sh render-final-summary.sh calls do not pass SESSION_ID and ISSUE_NUMBER into the child environment. Scenario: render-final-summary.sh reads SESSION_ID and ISSUE_NUMBER from env; the planned driver only exports DESIGN_TMPDIR, so approved designs render as run unknown / issue N/A and skip the larch:final-summary upsert even though the plan says the helper upserts it internally
- **Proposed resolution**: Invoke render-final-summary.sh with DESIGN_TMPDIR="$DESIGN_TMPDIR" SESSION_ID="$SESSION_ID" ISSUE_NUMBER="$ISSUE" and add test-design-publish.sh assertions that pre, post, and failed-plan-write render calls receive those env values

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:design-publish item 9
- **Concern**: design-log-publish stdout not captured. Scenario: Plan runs publish with stderr redirect only; PUBLISH_OK= is emitted on stdout so rename gating and WARN append never see publish outcome
- **Proposed resolution**: Use the existing subshell capture: set +e; _publish_out=$(design-log-publish.sh ... 2> ...); _publish_rc=$?; set -e; parse PUBLISH_OK from _publish_out

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh (proposed); skills/design/scripts/render-final-summary.sh:30-67,491-505
- **Concern**: Driver argv is not re-exported for render-final-summary.sh. Scenario: render-final-summary.sh reads DESIGN_TMPDIR SESSION_ID and ISSUE_NUMBER from env, not argv. If the parent env is missing, stale, or SESSION_ID is intentionally empty, the final summary can show the wrong run or issue and skip or misdirect the larch:final-summary upsert.
- **Proposed resolution**: After argv validation, export DESIGN_TMPDIR, ISSUE_NUMBER="$ISSUE", SESSION_ID="$SESSION_ID", and CLAUDE_PLUGIN_ROOT before any render-final-summary.sh call. Add harness assertions that the render stub sees those env values, including empty SESSION_ID.

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:33; skills/design/SKILL.md:1305
- **Concern**: Existing no-PUBLISH_OK failure branch is not preserved. Scenario: The current Step 5c contract treats a nonzero design-log-publish.sh exit without a PUBLISH_OK line as an unexpected shell failure. The proposed item 9 only handles PUBLISH_OK=false, so an early helper crash can leave PUBLISH_OK empty, skip rename and cleanup, but record no warning.
- **Proposed resolution**: Preserve the existing branch: if publish rc is nonzero and no PUBLISH_OK line was parsed, set PUBLISH_OK=false and append design-log-publish.failure.log under Warnings or fail explicitly. Add a test where the publish stub exits nonzero without PUBLISH_OK.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1305-1306
- **Concern**: Plan item 9 runs design-log-publish.sh with stderr redirected but does not capture stdout for PUBLISH_OK parsing. Scenario: PUBLISH_OK never parsed; rename gating and WARN append for publish failure diverge from today (often wrong skip/continue)
- **Proposed resolution**: Port the existing capture: _publish_out=$(design-log-publish.sh ... 2>design-log-publish.failure.log); parse PUBLISH_OK from _publish_out; preserve the non-zero-rc without PUBLISH_OK= branch

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh (planned); skills/design/scripts/render-final-summary.sh:10,58-66
- **Concern**: Planned driver does not explicitly export SESSION_ID and ISSUE_NUMBER before calling render-final-summary.sh. Scenario: render-final-summary.sh reads SESSION_ID and ISSUE_NUMBER from environment, so a direct driver run or stale/missing sourced env can render runid=unknown, omit or mis-target the summary upsert, or make the empty-SESSION_ID path inherit stale state
- **Proposed resolution**: Inside design-publish.sh, set and export SESSION_ID from --session-id and ISSUE_NUMBER from --issue before every render-final-summary.sh call; add a harness assertion that the stub sees those env values

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:1305; skills/design/scripts/design-publish.sh (planned)
- **Concern**: Plan omits the current unexpected publish-failure branch when design-log-publish.sh exits nonzero without PUBLISH_OK. Scenario: An early shell/tool crash can leave PUBLISH_OK empty, skip rename, and avoid appending the captured failure log, reducing recovery visibility compared with the current Step 5c contract
- **Proposed resolution**: Preserve the existing branch: when publish rc is nonzero and no PUBLISH_OK line was parsed, treat it as PUBLISH_OK=false, append design-log-publish.failure.log under Warnings with the rc, and keep rename skipped

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:item 9
- **Concern**: `design-log-publish.sh` invocation omits stdout capture. Scenario: `PUBLISH_OK` is emitted on stdout by `design-log-publish.sh`; the plan’s item 9 only redirects stderr to `design-log-publish.failure.log` and never assigns `_publish_out=$(...)`, so the driver cannot parse `PUBLISH_OK` and rename gating breaks (always skip or wrong branch)
- **Proposed resolution**: Mirror current SKILL item 9: `_publish_out=$("$PLUGIN_ROOT/scripts/design-log-publish.sh" … 2> "$DESIGN_TMPDIR/design-log-publish.failure.log")`; parse `PUBLISH_OK` from `_publish_out`; assert in `test-design-publish.sh`

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:NEW
- **Concern**: Driver plan calls render-final-summary.sh without binding ISSUE_NUMBER and SESSION_ID from its validated argv. Scenario: If inherited env is absent or stale, final-summary.md can show run unknown or upsert larch:final-summary to a different issue than plan-block-write used
- **Proposed resolution**: Export ISSUE_NUMBER="$ISSUE" and SESSION_ID="$SESSION_ID" after argv validation, or pass them as inline env on each render-final-summary.sh call

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/render-final-summary.sh:8-10,30,56-67,491-505
- **Concern**: design-publish plan does not require exporting or prefixing DESIGN_TMPDIR, SESSION_ID, and ISSUE_NUMBER before invoking render-final-summary.sh. Scenario: The new driver receives issue/session via argv, but render-final-summary.sh reads env; a literal implementation can render runid=unknown, skip larch:final-summary upsert, or fail if DESIGN_TMPDIR is not exported
- **Proposed resolution**: In design-publish.sh setup, export DESIGN_TMPDIR and SESSION_ID and set/export ISSUE_NUMBER="$ISSUE" (or prefix each render-final-summary.sh call); add a harness assertion that the render stub sees those env vars

### FINDING_12:
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-publish-ordering
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:1295-1298
- **Concern**: Plan moves fallback REPO resolution before plan-block-write even though current Step 5c resolves only after a successful plan write and explicitly skips resolution on plan-write failure. Scenario: This adds an unnecessary resolve-repo/gh call before the critical publish mutation and drifts from pure extraction/minimum-change ordering
- **Proposed resolution**: Keep only caller-provided REPO before plan-block-write; perform fallback resolve after plan-block-write succeeds, and render failed-plan-write summary with existing/provided REPO or no repo

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-phase-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1308
- **Concern**: Step 5c `.completed/step-5c` sentinel not carried into driver extraction. Scenario: Plan moves items 4–11 into `design-publish.sh` but never re-homes the success-boundary sentinel; `assert_step_completion_sentinels` still requires `.completed/step-5c` in the Step 5c SKILL window (scripts/test-design-structure.sh:993-994)
- **Proposed resolution**: Pause/resume and completion tracking can skip recording 5c success; CI structure test fails Add one orchestrator line after successful driver handoff when parsed `PLAN_WRITE_OK=true`: write `.completed/step-5c` before Step 5d (mirror current SKILL.md:1308); pin in test-design-structure if needed

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-phase-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lib-quiet.sh:5-7,73-78,158-178; skills/design/SKILL.md:1305
- **Concern**: The proposed SESSION_ID-empty warning is printed inside a quiet phase driver, so ordinary printf output will be redirected to the quiet log instead of reaching the orchestrator.. Scenario: When SESSION_ID is empty, design-publish.sh skips publish/rename but the user-visible warning promised by current Step 5c can disappear.
- **Proposed resolution**: Use emit or larch_err for that warning, or carry it as WARN= in .design-publish-result.env and have SKILL.md print it after parsing.

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-publish-ordering
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/render-final-summary.sh:50-76; skills/design/SKILL.md:1304-1306
- **Concern**: Finding 1: proposed design-publish.sh invokes render-final-summary.sh from parsed argv but does not require exporting ISSUE_NUMBER and SESSION_ID from --issue and --session-id.. Scenario: render-final-summary.sh reads DESIGN_TMPDIR, SESSION_ID, and ISSUE_NUMBER from environment; if the new driver relies only on argv, final-summary.md can show run unknown or Issue N/A and skip the larch:final-summary upsert.
- **Proposed resolution**: In design-publish.sh export SESSION_ID and ISSUE_NUMBER="$ISSUE" after argv validation and before every render-final-summary.sh call; add a harness assertion that the render stub sees both env vars.

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-publish-ordering
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1305
- **Concern**: Finding 2: the plan drops the current branch for design-log-publish.sh exiting nonzero without any PUBLISH_OK line.. Scenario: If design-log-publish.sh crashes before emitting PUBLISH_OK, PUBLISH_OK stays empty; rename is skipped, but the failure is no longer treated as the current unexpected shell failure and may not be recorded in Warnings.
- **Proposed resolution**: Port the exact current capture semantics: parse stdout regardless of rc, and when rc is nonzero with no PUBLISH_OK line, handle it as an unexpected publish failure, append design-log-publish.failure.log under Warnings, keep cleanup skipped, and cover this case in test-design-publish.sh.

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-publish-ordering
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1295-1296; skills/design/SKILL.md:420-446
- **Concern**: Finding 3: the SKILL.md rewrite description is internally inconsistent about emitting final-summary.md on PLAN_WRITE_OK=false.. Scenario: The plan-block-write failure path currently renders and emits the failed-plan-write summary before the warning; the proposed SKILL rewrite text only says to apply the shared full-body emit on success, so an implementer could print only the warning and skip the failure summary.
- **Proposed resolution**: Make the Step 5c post-driver branch explicitly emit FINAL_SUMMARY_PATH for both PLAN_WRITE_OK=false and PLAN_WRITE_OK=true before the warning/footer decision; keep the success-only 5c.5 status line separate.

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-drift-harness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:1032-1046
- **Concern**: Plan re-points Step 5c helper/order greps at 348-363 but omits Check 25, which still awk-scans SKILL.md Step 5c for design_reentry_marker_write before tracking-issue-write rename. Scenario: After items 4-11 move into design-publish.sh, Check 25 finds no tokens in the SKILL 5c window and test-design-structure fails despite the new driver pins
- **Proposed resolution**: Add an explicit UPDATED step: replace the Check 25 SKILL.md awk block with a design-publish.sh line-order pin (or drop Check 25 only if the planned marker-before-rename grep fully subsumes it)

### FINDING_19:
- **Reviewer(s)**: Codex-dyn-drift-harness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-render-cost-line-callsites.sh:59-68
- **Concern**: The plan re-points Step 5c pins only in test-design-structure, but this separate harness still pins old inline Step 5c item 10 prose.. Scenario: After SKILL.md replaces items 4-11 with the driver, make test-render-cost-line-callsites will fail or stale inline item-10 prose may be kept just to satisfy the pin.
- **Proposed resolution**: Update this harness to pin the new post-driver final-summary full-body emit contract, or keep the exact helper-exit sentence at the new driver-return callsite.

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-drift-harness
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:976-1003,1381-1403
- **Concern**: The plan adds Makefile-only test-design-publish.sh and test-design-publish.md but omits the existing agent-lint exclusion pattern for skill-local harnesses.. Scenario: agent-lint --pedantic from relevant-checks or make lint can flag the new harness and sibling doc as dead because agent-lint does not follow Makefile-only references.
- **Proposed resolution**: Add skills/design/scripts/test-design-publish.sh and skills/design/scripts/test-design-publish.md beside the existing test-design-driver exclusions.
