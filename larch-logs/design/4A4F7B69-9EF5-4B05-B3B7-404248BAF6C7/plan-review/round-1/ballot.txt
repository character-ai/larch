### FINDING_1: design-log-publish stdout not captured for PUBLISH_OK parsing
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned Step 5c / `design-publish.sh` driver invokes `design-log-publish.sh` with stderr redirected but does not capture stdout. `PUBLISH_OK` (and related publish status) is emitted on stdout, so the driver never parses publish outcome. Rename gating (`PUBLISH_OK=true`), warning append on failure, and status-line behavior drift from current `SKILL.md` Step 5c.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror `design-route.sh` / current Step 5c item 9: `set +e; _publish_out=$("$PLUGIN_ROOT/scripts/design-log-publish.sh" … 2> "$DESIGN_TMPDIR/design-log-publish.failure.log"); _publish_rc=$?; set -e` then parse `_publish_out`; for upsert `set +e; _upsert_out=$("$PLUGIN_ROOT/scripts/upsert-diagrams-comment.sh" …); _upsert_rc=$?; set -e` then parse `_upsert_out` (optionally keep `diagrams-architecture-upsert.{stdout,stderr}` captures); preserve the `_publish_rc` non-zero && no `PUBLISH_OK=` unexpected-failure branch from `skills/design/SKILL.md:1305`
  - From Cursor-Edge: Use the existing subshell capture: set +e; _publish_out=$(design-log-publish.sh ... 2> ...); _publish_rc=$?; set -e; parse PUBLISH_OK from _publish_out
  - From Cursor-Innovation: Port the existing capture: _publish_out=$(design-log-publish.sh ... 2>design-log-publish.failure.log); parse PUBLISH_OK from _publish_out; preserve the non-zero-rc without PUBLISH_OK= branch
  - From Cursor-Pragmatic: Mirror current SKILL item 9: `_publish_out=$("$PLUGIN_ROOT/scripts/design-log-publish.sh" … 2> "$DESIGN_TMPDIR/design-log-publish.failure.log")`; parse `PUBLISH_OK` from `_publish_out`; assert in `test-design-publish.sh`

### FINDING_2: upsert-diagrams-comment stdout not captured for UPSERT_STATUS parsing
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Plan driver pseudocode omits stdout capture for the `upsert-diagrams-comment.sh` emit_kv helper. `UPSERT_STATUS` / `ARCHITECTURE_SOURCE` are emitted on stdout; planned item 7 has no `_upsert_out=$(…)` capture, so parsing never runs and the `⏩ 5c.5` status line drifts from current Step 5c behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror `design-route.sh` / current Step 5c item 9: `set +e; _publish_out=$("$PLUGIN_ROOT/scripts/design-log-publish.sh" … 2> "$DESIGN_TMPDIR/design-log-publish.failure.log"); _publish_rc=$?; set -e` then parse `_publish_out`; for upsert `set +e; _upsert_out=$("$PLUGIN_ROOT/scripts/upsert-diagrams-comment.sh" …); _upsert_rc=$?; set -e` then parse `_upsert_out` (optionally keep `diagrams-architecture-upsert.{stdout,stderr}` captures); preserve the `_publish_rc` non-zero && no `PUBLISH_OK=` unexpected-failure branch from `skills/design/SKILL.md:1305`

### FINDING_3: render-final-summary.sh env not bound from driver argv
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-publish-ordering
- **Severity**: important
- **Concern**: Planned `design-publish.sh` calls `render-final-summary.sh` without exporting `SESSION_ID` and `ISSUE_NUMBER` (and in some paths `DESIGN_TMPDIR`) from validated argv into the child environment. `render-final-summary.sh` reads those values from env, not argv; missing, stale, or intentionally empty inherited env can render `run unknown` / issue N/A, skip or mis-target the `larch:final-summary` upsert, or inherit stale session state despite the plan assuming the helper upserts internally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Invoke render-final-summary.sh with DESIGN_TMPDIR="$DESIGN_TMPDIR" SESSION_ID="$SESSION_ID" ISSUE_NUMBER="$ISSUE" and add test-design-publish.sh assertions that pre, post, and failed-plan-write render calls receive those env values
  - From Codex-Edge: After argv validation, export DESIGN_TMPDIR, ISSUE_NUMBER="$ISSUE", SESSION_ID="$SESSION_ID", and CLAUDE_PLUGIN_ROOT before any render-final-summary.sh call. Add harness assertions that the render stub sees those env values, including empty SESSION_ID.
  - From Codex-Innovation: Inside design-publish.sh, set and export SESSION_ID from --session-id and ISSUE_NUMBER from --issue before every render-final-summary.sh call; add a harness assertion that the stub sees those env values
  - From Codex-Pragmatic: Export ISSUE_NUMBER="$ISSUE" and SESSION_ID="$SESSION_ID" after argv validation, or pass them as inline env on each render-final-summary.sh call
  - From Codex-Requirements: In design-publish.sh setup, export DESIGN_TMPDIR and SESSION_ID and set/export ISSUE_NUMBER="$ISSUE" (or prefix each render-final-summary.sh call); add a harness assertion that the render stub sees those env vars
  - From Codex-dyn-publish-ordering: In design-publish.sh export SESSION_ID and ISSUE_NUMBER="$ISSUE" after argv validation and before every render-final-summary.sh call; add a harness assertion that the render stub sees both env vars.

### FINDING_4: unexpected publish failure branch (nonzero rc, no PUBLISH_OK line) dropped
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-dyn-publish-ordering
- **Severity**: important
- **Concern**: Current Step 5c treats a nonzero `design-log-publish.sh` exit with no parsed `PUBLISH_OK` line as an unexpected shell failure (warn, skip rename). The proposed item 9 / driver plan only handles explicit `PUBLISH_OK=false`; an early helper crash can leave `PUBLISH_OK` empty, skip rename and cleanup, and record no warning—reducing recovery visibility vs today's contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Preserve the existing branch: if publish rc is nonzero and no PUBLISH_OK line was parsed, set PUBLISH_OK=false and append design-log-publish.failure.log under Warnings or fail explicitly. Add a test where the publish stub exits nonzero without PUBLISH_OK.
  - From Codex-Innovation: Preserve the existing branch: when publish rc is nonzero and no PUBLISH_OK line was parsed, treat it as PUBLISH_OK=false, append design-log-publish.failure.log under Warnings with the rc, and keep rename skipped
  - From Codex-dyn-publish-ordering: Port the exact current capture semantics: parse stdout regardless of rc, and when rc is nonzero with no PUBLISH_OK line, handle it as an unexpected publish failure, append design-log-publish.failure.log under Warnings, keep cleanup skipped, and cover this case in test-design-publish.sh.

### FINDING_5: REPO fallback resolution moved before plan-block-write
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-publish-ordering
- **Severity**: latent
- **Concern**: Plan moves fallback `REPO` resolution before `plan-block-write` even though current Step 5c resolves only after a successful plan write and explicitly skips resolution on plan-write failure. This adds an unnecessary resolve-repo/gh call before the critical publish mutation and drifts from pure extraction / minimum-change ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Keep only caller-provided REPO before plan-block-write; perform fallback resolve after plan-block-write succeeds, and render failed-plan-write summary with existing/provided REPO or no repo
  - From Codex-dyn-publish-ordering: Keep only caller-provided REPO before plan-block-write; perform fallback resolve after plan-block-write succeeds, and render failed-plan-write summary with existing/provided REPO or no repo

### FINDING_6: Step 5c `.completed/step-5c` sentinel not re-homed after driver extraction
- **Reviewer(s)**: Cursor-dyn-phase-contract
- **Severity**: important
- **Concern**: Plan moves Step 5c items 4–11 into `design-publish.sh` but does not carry the success-boundary `.completed/step-5c` sentinel into the orchestrator SKILL window. Pause/resume and completion tracking can skip recording 5c success; `assert_step_completion_sentinels` in `scripts/test-design-structure.sh` still requires `.completed/step-5c` in the Step 5c SKILL window.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-phase-contract: Pause/resume and completion tracking can skip recording 5c success; CI structure test fails Add one orchestrator line after successful driver handoff when parsed `PLAN_WRITE_OK=true`: write `.completed/step-5c` before Step 5d (mirror current SKILL.md:1308); pin in test-design-structure if needed

### FINDING_7: SESSION_ID-empty warning lost inside quiet-phase driver
- **Reviewer(s)**: Codex-dyn-phase-contract
- **Severity**: important
- **Concern**: The proposed `SESSION_ID`-empty warning is printed inside a quiet-phase driver, so ordinary `printf` output is redirected to the quiet log instead of reaching the orchestrator. When `SESSION_ID` is empty, `design-publish.sh` skips publish/rename but the user-visible warning promised by current Step 5c can disappear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-phase-contract: Use emit or larch_err for that warning, or carry it as WARN= in .design-publish-result.env and have SKILL.md print it after parsing.

### FINDING_8: SKILL rewrite omits failed-plan-write final-summary emit contract
- **Reviewer(s)**: Codex-dyn-publish-ordering
- **Severity**: important
- **Concern**: The planned `SKILL.md` rewrite is internally inconsistent about emitting `final-summary.md` on `PLAN_WRITE_OK=false`. Current Step 5c renders and emits the failed-plan-write summary before the warning; proposed rewrite text only describes the shared full-body emit on success, so an implementer could print only the warning and skip the failure summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-publish-ordering: Make the Step 5c post-driver branch explicitly emit FINAL_SUMMARY_PATH for both PLAN_WRITE_OK=false and PLAN_WRITE_OK=true before the warning/footer decision; keep the success-only 5c.5 status line separate.

### FINDING_9: test-design-structure Check 25 still awk-scans moved inline prose
- **Reviewer(s)**: Cursor-dyn-drift-harness
- **Severity**: important
- **Concern**: Plan re-points Step 5c helper/order greps at lines 348–363 but omits Check 25, which still awk-scans `SKILL.md` Step 5c for `design_reentry_marker_write` before `tracking-issue-write` rename. After items 4–11 move into `design-publish.sh`, Check 25 finds no tokens in the SKILL 5c window and `test-design-structure` fails despite new driver pins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-drift-harness: Add an explicit UPDATED step: replace the Check 25 SKILL.md awk block with a design-publish.sh line-order pin (or drop Check 25 only if the planned marker-before-rename grep fully subsumes it)

### FINDING_10: test-render-cost-line-callsites still pins old inline Step 5c item 10
- **Reviewer(s)**: Codex-dyn-drift-harness
- **Severity**: important
- **Concern**: Plan re-points Step 5c pins only in `test-design-structure.sh`, but `scripts/test-render-cost-line-callsites.sh` still pins old inline Step 5c item 10 prose. After `SKILL.md` replaces items 4–11 with the driver, `make test-render-cost-line-callsites` will fail or stale inline item-10 prose may be kept just to satisfy the pin.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-drift-harness: Update this harness to pin the new post-driver final-summary full-body emit contract, or keep the exact helper-exit sentence at the new driver-return callsite.

### FINDING_11: agent-lint exclusions missing for new design-publish harness
- **Reviewer(s)**: Codex-dyn-drift-harness
- **Severity**: important
- **Concern**: Plan adds Makefile-only `test-design-publish.sh` and `test-design-publish.md` but omits the existing `agent-lint.toml` exclusion pattern for skill-local harnesses. `agent-lint --pedantic` from `relevant-checks` or `make lint` can flag the new harness and sibling doc as dead because agent-lint does not follow Makefile-only references.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-drift-harness: Add skills/design/scripts/test-design-publish.sh and skills/design/scripts/test-design-publish.md beside the existing test-design-driver exclusions.

---

**Merge summary**: 20 source findings consolidated into 11 distinct behavioral risks. Input `FINDING_3`, `6`, `9` merged into **FINDING_1**; input `FINDING_4`, `7`, `10`, `11`, `15` merged into **FINDING_3**; input `FINDING_5`, `8`, `16` merged into **FINDING_4**; input `FINDING_12` merged into **FINDING_5**; upsert capture split from Cursor-Arch input `FINDING_1` as **FINDING_2** (distinct code path/fix).
