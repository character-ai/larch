### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:59-61
- **Concern**: Structure pin requires rename before the first design-log-publish.sh line. Scenario: Post-change order is upsert → design-log-publish.sh --scrub-only → rename → full flush; publish_log_line is the scrub-only call, so publish_rename_line < publish_log_line fails on a correct implementation and the new pin fights check (25)
- **Proposed resolution**: Use separate line anchors (e.g. scrub-only vs full-flush grep) and assert upsert < scrub < rename < full_flush < marker; drop rename-before-first-design-log-publish

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-publish.sh:46-47,78-91
- **Concern**: Happy-path ordering and default publish stub omit --scrub-only. Scenario: Stub never emits SCRUB_OK=true for --scrub-only, so rename stays gated off; planned rename_pos < publish_pos also fails because the first design-log-publish log line is scrub-only before rename
- **Proposed resolution**: Update stub to branch on --scrub-only (default SCRUB_OK=true; SCRUB_OK=false only in the new case); assert upsert < scrub-only < rename < full publish < marker (two publish positions or --scrub-only-aware grep)

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:323-330 / skills/design/scripts/render-final-summary.sh:300-315
- **Concern**: append_failed_publish_notes is told to read RENAMED from .design-publish-result.env but render-final-summary runs before write_result_env_and_emit. Scenario: Rename runs before render; result env is not written yet, so failed-publish summary cannot qualify on RENAMED and may falsely promise or deny /implement admission
- **Proposed resolution**: Export RENAMED (mirror DESIGN_LOG_* exports before render) and have append_failed_publish_notes read RENAMED from the environment; align test-render-final-summary to set/export RENAMED, not only a post-hoc result file

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/design-publish.sh:272-276 / plan.txt:14
- **Concern**: Scrub-only stdout may carry SECRET_SCRUB_VIOLATIONS but the plan does not wire add_warn from the pre-rename scrub path. Scenario: Early [DESIGNED] admission can precede full publish; if full publish fails before its scrub pass, the rotation WARN never fires despite scrub-only having already seen violations
- **Proposed resolution**: Parse SECRET_SCRUB_VIOLATIONS from --scrub-only output and emit the same add_warn before rename (keep or dedupe if full publish repeats the count)

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-design-publish.sh:246-256; scripts/test-design-structure.sh:634-636,1327-1331
- **Concern**: The planned order checks treat the first design-log-publish occurrence as the full publish after adding an earlier --scrub-only call. Scenario: The new scrub-only call must occur before rename, so head -1 / first-match publish_pos will either fail the planned plan→upsert→rename→publish assertion or pin the wrong order
- **Proposed resolution**: Track scrub_pos and publish_full_pos separately; assert upsert < scrub_only < rename < full_publish < marker, and make the default stub emit SCRUB_OK=true for --scrub-only

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:323-330,367-368; skills/design/scripts/render-final-summary.sh:300-315
- **Concern**: Failed-publish summary has no reliable RENAMED input. Scenario: render-final-summary runs before .design-publish-result.env is written, so reading RENAMED only from that file can render rename-failure guidance even after RENAMED=true
- **Proposed resolution**: Export or otherwise pass RENAMED to render-final-summary before the post-publish call; keep result-env reading only as a standalone fallback

### FINDING_7:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/design-log-publish.sh; scripts/test-design-log-publish.sh
- **Concern**: New --scrub-only mode is not directly tested in the script harness. Scenario: design-publish stub tests can pass while the real mode still creates PRs, pushes, emits only PUBLISH_OK, or fails to return SCRUB_OK=false on scrub failure
- **Proposed resolution**: Add minimal test-design-log-publish cases for --scrub-only success and scrub failure: emits SCRUB_OK, propagates SECRET_SCRUB_VIOLATIONS when present, and never reaches PR/push/merge flow

### FINDING_8:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/render-final-summary.sh:300-315
- **Concern**: Failed-publish admission bullet reads RENAMED from result env before it exists. Scenario: After early rename + failed log flush, summary omits or misstates /implement readiness; operators trust wrong footer
- **Proposed resolution**: before render, export RENAMED from design-publish (or write RENAMED into result env); have append_failed_publish_notes prefer env with optional file fallback; align render-final-summary.md

### FINDING_9:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:634-636,1327-1331
- **Concern**: New ordering pin uses first design-log-publish line (scrub-only). Scenario: Structure test fails on correct script layout or passes with rename before full flush
- **Proposed resolution**: Define publish_log_line as full-flush line only; keep separate scrub_line if needed

### FINDING_10:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-publish.sh:246-254
- **Concern**: Happy-path publish_pos uses first CALL_LOG design-log-publish entry. Scenario: Harness fails rename-before-publish ordering on valid implementation
- **Proposed resolution**: Set publish_pos to last design-log-publish line or exclude --scrub-only from the match

### FINDING_11:
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-scrub-gate
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-publish.sh:78-91
- **Concern**: Stub lacks SCRUB_OK=true for --scrub-only. Scenario: Rename never runs in harness; new rename assertions fail
- **Proposed resolution**: Update stub to emit SCRUB_OK=true for --scrub-only by default; keep SCRUB_OK=false case explicit

### FINDING_12:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-publish.sh:272-276
- **Concern**: Scrub-only SECRET_SCRUB_VIOLATIONS not wired to add_warn. Scenario: Early rename allowed but rotation WARN missing when full publish aborts early
- **Proposed resolution**: Parse SECRET_SCRUB_VIOLATIONS from scrub-only stdout and reuse existing SECURITY warn before rename

### FINDING_13:
- **Reviewer(s)**: Codex-Edge, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:323-330,367-368; skills/design/scripts/render-final-summary.sh:300-315
- **Concern**: Failed-publish summary is planned to qualify /implement admission from RENAMED in .design-publish-result.env, but design-publish renders the summary before writing that env file and the plan does not pass RENAMED to the renderer.. Scenario: When rename succeeds and full publish fails, final-summary cannot know RENAMED=true and may omit the intended admission-ready guidance; when rename fails, any default/old value could over-promise readiness.
- **Proposed resolution**: Pass the current RENAMED value to render-final-summary before the post-publish render, for example export RENAMED and make the renderer prefer that over result-env fallback; add an integration assertion in test-design-publish for failed-publish render env with RENAMED=true and RENAMED=false.

### FINDING_14:
- **Reviewer(s)**: Codex-Edge, Codex-dyn-scrub-gate
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:632-636,1326-1331; skills/design/scripts/test-design-publish.sh:78-81,246-254
- **Concern**: The planned order checks still treat the first design-log-publish occurrence as the full publish call, but the proposed code adds a design-log-publish.sh --scrub-only call before rename.. Scenario: A correct implementation logs scrub-only before rename, so the proposed plan→upsert→rename→publish→marker and upsert<rename<publish_log assertions fail, or a hidden scrub-only log path loses coverage.
- **Proposed resolution**: Split scrub-only and full-publish positions in both harnesses; tag the stub log lines, then assert plan < upsert < scrub-only < rename < full-publish < marker while keeping duplicate-rename coverage.

### FINDING_15:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:634-636,59-61
- **Concern**: Proposed pin uses first `design-log-publish.sh` line as `publish_log_line`. Scenario: After `--scrub-only`, the first `design-log-publish.sh` match is scrub preflight, not full flush; `publish_upsert_line < publish_rename_line < publish_log_line` incorrectly requires rename before scrub and does not pin rename before full publish
- **Proposed resolution**: Track separate line vars (e.g. `publish_scrub_line` = first match, `publish_flush_line` = last or match without `--scrub-only`); assert `upsert < scrub < rename < flush`

### FINDING_16:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:632-635; skills/design/scripts/test-design-publish.sh:246-254
- **Concern**: The planned order pins still use the first design-log-publish occurrence as the publish position, but the new --scrub-only call is also design-log-publish and intentionally runs before rename.. Scenario: A correct implementation with upsert -> scrub-only -> rename -> full publish will fail the proposed upsert < rename < publish_log and happy-path first-match assertions, or tests may be weakened by hiding the scrub-only call from greps.
- **Proposed resolution**: Split scrub and full-publish positions in both harnesses, matching --scrub-only separately from the full publish call, then assert plan/upsert < scrub-only < rename < full publish < marker.

### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:634-636
- **Concern**: skills/design/scripts/test-design-publish.sh:246-254. Scenario: New ordering pins reuse first design-log-publish.sh line number
- **Proposed resolution**: After two publish calls (--scrub-only then full flush) publish_log_line and harness publish_pos still use head -1 so they anchor the scrub call before rename; new upsert<rename<publish_log pin and happy-path plan<upsert<rename<publish<marker ordering fail or pass incorrectly Define publish_log_line (and harness publish_pos) from the full-flush invocation only (e.g. last match or grep excluding --scrub-only); keep scrub-before-rename as a separate pin if needed

### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-publish.sh:247-254; scripts/test-design-structure.sh:634-636,1329-1333
- **Concern**: Proposed order assertions omit the new pre-rename design-log-publish.sh --scrub-only call. Scenario: Post-change call order is plan upsert scrub-only rename full-publish marker, so grep/head -1 publish positions will precede rename and fail or encourage hiding the scrub call
- **Proposed resolution**: Pin plan < upsert < scrub-only < rename < full-publish < marker; compute scrub and full publish positions with patterns that distinguish --scrub-only

### FINDING_19:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:323-330,367-369; skills/design/scripts/render-final-summary.sh:300-315
- **Concern**: Failed-publish summary is planned to read RENAMED from .design-publish-result.env, but design-publish renders before writing that file. Scenario: A log-publish failure after an early rename can render admission guidance from missing or stale rename state
- **Proposed resolution**: Export current rename/admission state before invoking render-final-summary.sh, or write current result state before render; do not rely on the final result-env write

### FINDING_20:
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-contract-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/tracking-issue-write.sh:487-492; skills/design/scripts/test-render-final-summary.sh:522-531
- **Concern**: Plan treats RENAMED=false as rename failure, but tracking-issue-write uses RENAMED=false for a successful no-op when the title is already canonical. Scenario: A failed publish with an already [DESIGNED] title could tell operators to fix a rename and delay /implement even though admission is ready
- **Proposed resolution**: Track rename failure separately from no-op, e.g. parse NEW_TITLE or set TITLE_DESIGNED/RENAME_ERROR, and make failed-publish prose/tests use admission state rather than RENAMED=false

### FINDING_21:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/design-log-publish.sh:49-91; scripts/test-design-log-publish.sh:390-455
- **Concern**: New --scrub-only mode lacks a direct harness in the script that implements it. Scenario: design-publish stubs can pass while real --scrub-only still emits PUBLISH_OK, continues into PR creation, or fails to emit SCRUB_OK on scrub failure
- **Proposed resolution**: Add minimal test-design-log-publish.sh cases for --scrub-only success and scrub-gate failure, asserting SCRUB_OK output and no gh push/pr/merge calls

### FINDING_22:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-publish.sh:246-256
- **Concern**: Happy-path ordering still keys publish_pos off the first design-log-publish.sh CALL_LOG line. Scenario: After --scrub-only is inserted before rename, the first log line is scrub-only (before rename), so plan_pos < upsert_pos < rename_pos < publish_pos fails on the intended happy path and blocks merge
- **Proposed resolution**: Pin scrub_pos and full-flush publish_pos separately (e.g. grep --scrub-only vs full call without that flag); assert plan < upsert < scrub < rename < full_publish < marker

### FINDING_23:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:323-330,367-368; skills/design/scripts/render-final-summary.sh:300-315
- **Concern**: Failed-publish admission notes have no reliable rename outcome data flow. Scenario: The plan tells render-final-summary.sh to qualify /implement admission using RENAMED from .design-publish-result.env, but design-publish.sh renders the summary before write_result_env_and_emit writes that file; a stale or missing env can make the failed-publish summary omit or misstate whether admission is ready.
- **Proposed resolution**: Pass the rename/title-ready outcome to render-final-summary.sh before rendering, such as an exported env var, and have tests cover RENAMED=true, rename failure, and already-[DESIGNED] no-op if that path remains promised.

### FINDING_24:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-design-publish.sh:247-255; scripts/test-design-structure.sh:632-636,1327-1333
- **Concern**: Ordering tests conflate scrub-only with full publish. Scenario: The proposed new first design-log-publish.sh call is --scrub-only, so using the first design-log-publish match as publish_pos or publish_log_line will either fail the intended rename-before-full-publish assertion or pin the wrong order.
- **Proposed resolution**: Track scrub_pos separately from full_publish_pos. Assert plan < upsert < scrub-only < rename < full publish < marker, and make the structure test locate the non---scrub-only full publish call before comparing against rename.

### FINDING_25:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/test-design-log-publish.sh:337-445; scripts/design-log-publish.md:238-239
- **Concern**: New --scrub-only mode lacks a direct harness requirement. Scenario: The plan adds security-critical behavior to design-log-publish.sh but only stubs it through test-design-publish.sh; the real script could emit the wrong SCRUB_OK contract, push/create a PR, or skip the existing staging scrub path without a failing test.
- **Proposed resolution**: Add minimal test-design-log-publish.sh cases for --scrub-only success and fail-closed scrub failure, including SCRUB_OK output, SECRET_SCRUB_VIOLATIONS propagation when applicable, and no gh pr create/push/merge side effects; include this harness in the testing strategy.

### FINDING_26:
- **Reviewer(s)**: Cursor-dyn-contract-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:59-61
- **Concern**: Proposed pin uses publish_log_line before rename but publish_log_line is the first design-log-publish.sh match (scrub-only). Scenario: After two publish calls, rename line number exceeds first publish line; upsert < rename < publish_log_line fails on correct code
- **Proposed resolution**: Assert upsert < rename < last design-log-publish line (or a dedicated scrub-only line variable); do not reuse first-match publish_log_line for rename ordering

### FINDING_27:
- **Reviewer(s)**: Codex-dyn-contract-sync, Codex-dyn-scrub-gate
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-publish.sh:323-330,367-368; skills/design/scripts/render-final-summary.sh:300-315
- **Concern**: Plan says render-final-summary should read RENAMED from .design-publish-result.env, but the summary renders before design-publish writes that env file. Scenario: On publish failure after early rename, failed-publish summary cannot reliably know current rename outcome; it may read stale/absent env data and emit the wrong admission guidance
- **Proposed resolution**: Pass the live rename outcome into render-final-summary before invocation, e.g. export RENAMED/RENAME_STATUS or add an explicit flag, and update the renderer contract/tests to use that live value rather than the not-yet-written result env

### FINDING_28:
- **Reviewer(s)**: Codex-dyn-contract-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-publish.sh:246-256; scripts/test-design-structure.sh:632-636,1326-1331
- **Concern**: The proposed order assertions compare rename against the first design-log-publish occurrence, but the new scrub-only call is also design-log-publish and must occur before rename. Scenario: A correct implementation with upsert -> design-log-publish --scrub-only -> rename -> full design-log-publish will fail the planned plan→upsert→rename→publish assertions, or the test may accidentally force the scrub-only gate after rename
- **Proposed resolution**: Distinguish scrub-only from full publish in both harnesses: assert upsert < scrub-only < rename < full publish < marker, using a grep that excludes --scrub-only or uses the last design-log-publish line for the full publish position

### FINDING_29:
- **Reviewer(s)**: Cursor-dyn-scrub-gate
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:59-60
- **Concern**: Proposed upsert<rename<first-publish line pin contradicts scrub-only-before-rename order. Scenario: Structure test fails on correct code or passes if rename is wrongly placed before scrub preflight
- **Proposed resolution**: Pin upsert < first design-log-publish (scrub) < rename < last design-log-publish (flush); drop rename-before-first-publish assertion

### FINDING_30:
- **Reviewer(s)**: Cursor-dyn-scrub-gate
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-publish.sh:248-254
- **Concern**: Happy-path publish_pos uses first design-log-publish match after two calls. Scenario: rename_pos < publish_pos fails when scrub-only precedes rename
- **Proposed resolution**: Use last flush line or exclude --scrub-only; assert scrub < rename < flush in CALL_LOG

### FINDING_31:
- **Reviewer(s)**: Cursor-dyn-scrub-gate
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/design-publish.sh:272-276
- **Concern**: Plan omits SECRET_SCRUB_VIOLATIONS warn from --scrub-only parse before rename. Scenario: [DESIGNED] rename can precede ROTATE credential warning vs today’s publish→warn→rename order
- **Proposed resolution**: Parse SECRET_SCRUB_VIOLATIONS from scrub-only stdout and add_warn before rename; document in design-publish.md

### FINDING_32:
- **Reviewer(s)**: Cursor-dyn-admission-flow
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/render-final-summary.sh:300-315
- **Concern**: Failed-publish admission notes plan to read RENAMED from .design-publish-result.env but render runs before write_result_env_and_emit. Scenario: In design-publish.sh render-final-summary.sh is invoked before .design-publish-result.env is written (today at lines 326-330 vs 367; after reorder still before the final write_result_env_and_emit). append_failed_publish_notes cannot see RENAMED from that file during the live Step 5c render, so final-summary.md may omit the qualified /implement bullet even when rename succeeded and PUBLISH_OK=false
- **Proposed resolution**: Export RENAMED (and optional SCRUB_OK) in the environment immediately before calling render-final-summary.sh, mirroring DESIGN_LOG_PR_NUMBER/URL/RECOVERY_BRANCH (lines 323-325); have append_failed_publish_notes read those exports first and treat .design-publish-result.env as fallback only for offline harnesses

### FINDING_33:
- **Reviewer(s)**: Cursor-dyn-admission-flow
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:1550-1554
- **Concern**: Step 5d failed-publish footer still unconditional after early [DESIGNED] rename. Scenario: After reorder, PUBLISH_OK=false can occur with RENAMED=true and a [DESIGNED] title while the Step 5d footer remains log publish incomplete; NEXT REQUIRED: continue (lines 1550-1552), which still reads like full admission despite log flush failure
- **Proposed resolution**: Apply the plan's RENAMED/title qualification to the Step 5d footer itself (not only render-final-summary.md): when RENAMED=true or title is [DESIGNED], state that /implement may proceed and log recovery is separate; when RENAMED=false, point to the [DESIGNED] rename failed WARN

### FINDING_34:
- **Reviewer(s)**: Codex-dyn-admission-flow
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:319-330,367-368; skills/design/scripts/render-final-summary.sh:300-315
- **Concern**: Proposed failed-publish admission note reads RENAMED from .design-publish-result.env, but design-publish renders final-summary before writing that env. Scenario: On publish failure after rename failure or scrub skip, the summary can miss the current rename outcome or read stale state from a prior attempt, leaving operators with wrong /implement guidance
- **Proposed resolution**: Pass the current admission state to render-final-summary before it runs, for example via exported env such as DESIGN_PUBLISH_RENAMED and SCRUB_OK, or write a small current-state file before render; do not rely on the not-yet-written result env

### FINDING_35:
- **Reviewer(s)**: Codex-dyn-admission-flow
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/tracking-issue-write.sh:490-493; skills/design/scripts/design-publish.sh:332-347; skills/design/SKILL.md:1550-1554
- **Concern**: Plan treats RENAMED=false as rename-failure guidance, but tracking-issue-write uses RENAMED=false for an already-correct title and design-publish leaves RENAMED unset on command failure. Scenario: An already-[DESIGNED] no-op may be told to fix a rename, while an actual rename command failure or scrub-blocked skip may not hit the intended branch; scrub failure could incorrectly lead operators toward manual rename, bypassing the scrub gate
- **Proposed resolution**: Use an explicit admission/block state separate from RENAMED delta, e.g. ADMISSION_READY=true or ADMISSION_BLOCK_REASON=scrub-failed|rename-failed; only suggest manual rename for rename-failed, and tell scrub-failed operators to fix the exposure and retry Step 5c

### OOS_1:
- **Description**: No unit tests for --scrub-only mode. Scenario: Worktree/scrub contract regressions undetected until live /design
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-design-log-publish.sh
- **Phase**: design
