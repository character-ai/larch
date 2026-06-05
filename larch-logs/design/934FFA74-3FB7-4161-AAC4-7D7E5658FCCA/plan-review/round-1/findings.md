### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:699-764
- **Concern**: Plan folds step-2a into the Step 2a.5 prelude host, but HARD zero-sketch skips that entire section. Scenario: On both-tools-down zero-sketch, the run jumps to Step 2b without executing the 2a.5 prelude or the line-764 success-boundary write item 6 preserves, so step-2a may never be created while assert_folded_sentinel_writes still expects it in the 2a.5 fence
- **Proposed resolution**: Add an explicit step-2a write on the zero-sketch branch (skills/design/SKILL.md:699) or in the Step 2b prelude; extend assert_folded_sentinel_writes to accept that alternate host when the skip prose is present

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:528-532
- **Concern**: Step 0c combined Bash call omits the env-source contract. Scenario: Without sourcing current-design-env-$PPID.sh, the new step-0c/timing fence can fail on unset DESIGN_TMPDIR or skip pause handling at the first post-setup driver boundary
- **Proposed resolution**: Specify the fence as source-env, optional pause-check, then step-0c write and the block timing mark (mirror other driver fences)

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/step-name-registry.tsv:7, scripts/design-pause-save.sh:180-186, scripts/test-design-structure.sh:1683
- **Concern**: The plan leaves step-1d.7 sentinel-less while pause-save still treats 1d.7 as an ordered resumable step. Scenario: After a folded host writes later sentinels such as step-2a and then honors a pause, design-pause-save scans the registry, finds missing step-1d.7 before step-2a/2a.5, records STEP=1d.7, and resume can route back through outline handling instead of the intended forward boundary
- **Proposed resolution**: Add .completed/step-1d.7 to the folded/boundary writes before the Step 2a pause-check, or remove 1d.7 from the pause registry and update the pause tests; also include 1d.7 in the new folded-sentinel assertion so the contract is enforced

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:1771-1772
- **Concern**: Step 5c fold drops a pinned Check 15b prose substring. Scenario: Item 17 moves `step-5c` into the `design-publish.sh` fence and rewrites item 6 prose; Check 15b still greps for the exact backtick string ``: > "$DESIGN_TMPDIR/.completed/step-5c"` **only when** `PLAN_WRITE_OK=true`'' in `SKILL.md`. A literal follow of the plan can pass the new `assert_folded_sentinel_writes` checks yet fail `make test-design-structure` / `relevant-checks.sh`.
- **Proposed resolution**: Keep that exact substring in Step 5c item-6 prose (even when the write is in-fence), or extend the plan to update the Check 15b grep to match the in-fence `if [[ "${PLAN_WRITE_OK:-}" == true ]]` block.

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:528-532
- **Concern**: Step 0c proposed Bash call does not specify sourcing the current design env before using DESIGN_TMPDIR and CLAUDE_PLUGIN_ROOT. Scenario: A fresh Bash subshell does not preserve Step 0b variables, so the new combined step-0c plus discussion-block timing fence can fail or write to the wrong path before Step 1c starts
- **Proposed resolution**: Start the Step 0c fence by sourcing ~/.cache/larch/sessions/current-design-env-$PPID.sh before the mkdir and timing-ledger lines

### FINDING_6:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:1430-1448
- **Concern**: Folding step-5b into the Step 5c publish fence removes the last pause boundary before design-publish.sh. Scenario: When .pause-requested is set after OOS filing but before publish, the proposed no-pause Step 5c fence still proceeds to write the plan block, publish logs, and possibly rename the issue
- **Proposed resolution**: Keep the step-5b sentinel as a standalone boundary, or add an explicit pause-check before design-publish.sh after writing step-5b if that fence becomes the host

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:57-59
- **Concern**: assert_folded_sentinel_writes applies before-pause ordering to every host fence with a pause-check. Scenario: Step 6 item 19 places step-6 after pause-check and before cleanup-tmpdir.sh; the harness rule would reject that placement or force step-6 before pause-check so pause at cleanup resumes into a re-run of Step 6 cleanup
- **Proposed resolution**: Exempt step-6 from the before-pause ordering check or assert step-6 after design-pause-save.sh and before cleanup-tmpdir.sh instead

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:89-97; skills/design/SKILL.md:1446-1511
- **Concern**: Planned folded-sentinel test reuses a fence extractor that only matches unindented ```bash fences, but the Step 5c design-publish fence is indented inside a numbered list. Scenario: The new step-5b and step-5c assertions either cannot find the host fence and fail CI, or skip the only publish-hosted folded writes
- **Proposed resolution**: For the new assertion, add a minimal extractor that accepts optional leading whitespace around ```bash/``` or special-case the design-publish fence search before checking the two sentinel writes

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:19,59,86
- **Concern**: skills/design/SKILL.md Step 6 cleanup fence places step-6 after pause-check, but assert_folded_sentinel_writes requires all pause-bearing host fences to write before design-pause-save.sh. Scenario: Item 19 folds step-6 between pause-check and cleanup-tmpdir.sh; item 2/59 pins every pause host to source-env → sentinel → pause-check; implementing both forces step-6 before pause-check and breaks the stated cleanup-boundary semantics
- **Proposed resolution**: Exempt the cleanup-tmpdir.sh host from the before-pause ordering rule (or assert step-6 after pause-check and before cleanup-tmpdir.sh only); document step-6 as the sole deliberate exception in the audit table and failure-mode mitigation text

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:1390-1431; skills/design/scripts/design-publish.sh:330-331
- **Concern**: Plan moves .completed/step-5b into the Step 5c publish fence, self-satisfying design-publish.sh's OOS precondition. Scenario: If orchestration or resume reaches Step 5c with Step 5b not actually settled, the proposed fence creates the sentinel and publish proceeds instead of design-publish.sh refusing before plan publication
- **Proposed resolution**: Keep the step-5b sentinel at the Step 5b boundary, or fold it into Step 5b's own final settled branches, not into the Step 5c publish fence

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:36-39,61; scripts/test-design-structure.sh:99-143
- **Concern**: Plan moves `.completed/step-2a` and `step-2a.5` out of the Step 2a entry fence but leaves `assert_step2a_entry_simple_guard` unchanged. Scenario: Implementing items 6–8 removes the literals that guard requires inside the SIMPLE branch of the first fence after `<!-- step:2a —`; `make test-design-structure` fails while SKILL prose still claims the entry fence is the primary marker site
- **Proposed resolution**: Update the harness (and anti-pattern #1 / SIMPLE skip prose) so artifacts stay pinned in the Step 2a entry guard while `step-2a` is asserted in the `### 2a.5` prelude fence and `step-2a.5` in the Step 2b prelude fence; drop the “unchanged” claim on line 61

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:57-59; scripts/test-design-structure.sh:89-96; skills/design/SKILL.md:1446-1511
- **Concern**: `assert_folded_sentinel_writes` reuses `extract_first_bash_fence_after`, which only matches column-0 ` ```bash ` fences. Scenario: The Step 5c `design-publish.sh` fence is list-indented (`skills/design/SKILL.md:1446`); a host lookup after `### 5c` returns the Step 6 cleanup fence instead, so `step-5b` / `step-5c` pins never run or misfire
- **Proposed resolution**: Add a token-scoped extractor that accepts indented fence delimiters (or un-indent the publish fence) and use it for the `design-publish.sh` host pair only

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements, Codex-dyn-test-harness-gaps
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:50,57-59; skills/design/SKILL.md:1562-1567
- **Concern**: Generic “write before `design-pause-save.sh`” rule conflicts with the planned Step 6 cleanup fold. Scenario: Item 19 places `step-6` between pause-check and `cleanup-tmpdir.sh`; the proposed assertion would force `step-6` before pause-check and break the documented happy-path ordering
- **Proposed resolution**: Special-case `step-6` in `assert_folded_sentinel_writes`: require the literal after pause-check and before `cleanup-tmpdir.sh`; keep before-pause ordering for all other absorbed sentinels

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:6-8,78; skills/design/SKILL.md:104,651,679,815
- **Concern**: Edge-case text and multiple SIMPLE routing sites still say Step 2a entry writes `step-2a` / `step-2a.5` in one turn after items 6–8 relocate those writes. Scenario: Resume/skip prose and anti-pattern #1 can mislead the orchestrator on SIMPLE fresh runs and paused repair even if fences are edited
- **Proposed resolution**: Align edge-case § SIMPLE fresh run with the 2a.5 / 2b host-fence contract and update anti-pattern #1, § SIMPLE branch, § 2a.2, and the 2a.5 skip note to name the new write sites

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:89-97; skills/design/SKILL.md:1562-1567
- **Concern**: Planned folded-write assertion conflicts with Step 6 cleanup ordering. Scenario: The plan says Step 6 writes step-6 after the pause-check and before cleanup-tmpdir.sh, but the proposed assertion requires folded writes in pause-check hosts to appear before design-pause-save.sh; that either fails the intended implementation or pushes step-6 before the pause boundary.
- **Proposed resolution**: Special-case step-6 in assert_folded_sentinel_writes: require it after the pause-check and before cleanup-tmpdir.sh, while keeping before-pause ordering for absorbed prior-step sentinels.

### FINDING_16:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:89-97; skills/design/SKILL.md:1446-1511
- **Concern**: Existing fence extractor cannot validate the planned design-publish host fence. Scenario: The plan says to assert step-5b and step-5c inside the fence containing design-publish.sh while reusing extract_first_bash_fence_after, but that helper only matches unindented bash fences and has no contains-token mode; the Step 5c publish fence is indented inside a list item.
- **Proposed resolution**: Add a small fence extractor that accepts optional leading spaces and can locate a bash fence by contained token; use it for the design-publish.sh folded-write checks.

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-sentinel-ordering
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:57-59
- **Concern**: skills/design/SKILL.md:50-51. Scenario: Proposed assert_folded_sentinel_writes requires every sentinel in a pause-bearing host fence to sit after source-env and before design-pause-save.sh, but item 19 places step-6 after the pause-check and immediately before cleanup-tmpdir.sh (intentional so pause before cleanup does not mark step-6 complete).
- **Proposed resolution**: CI fails on the cleanup fence even when SKILL.md matches item 19, or an implementer "fixes" red CI by moving step-6 before pause-check and reintroduces failure mode 1 (resume skips cleanup). Exempt step-6 from the before-pause line-order rule in assert_folded_sentinel_writes (only require the literal in the cleanup-tmpdir fence), or assert step-6 is after pause-check and before cleanup-tmpdir.sh; align item 2 / the audit table with that exception.

### FINDING_18:
- **Reviewer(s)**: Codex-dyn-sentinel-ordering
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1555-1567
- **Concern**: Plan item 19 places the folded step-6 write after the cleanup fence pause-check. Scenario: The stated invariant says every .completed redirection in a host fence must be after source-env and before design-pause-save.sh; the proposed Step 6 cleanup shape instead writes step-6 between the pause-check and cleanup-tmpdir.sh, leaving one fold site outside the ordering contract and likely forcing a test exception
- **Proposed resolution**: Move the step-6 mkdir and redirection to immediately after the source-env line and before the pause-check in the cleanup fence, or explicitly remove Step 6 from the invariant and folded-write assertion

### FINDING_19:
- **Reviewer(s)**: Codex-dyn-sentinel-ordering
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:699-764
- **Concern**: Step 2a HARD zero-sketch path can lose its step-2a completion write when the shared success-boundary write moves to Step 2a.5. Scenario: The current zero-sketch route skips Step 2a.5 and relies on the shared Step 2a success-boundary prose for the step-2a marker; replacing that prose with a Step 2a.5-hosted write leaves HARD zero-sketch runs with step-2a missing, so later pause-save can route back before the completed sketch phase
- **Proposed resolution**: Add an explicit zero-sketch degraded-path instruction to write mkdir -p "$DESIGN_TMPDIR/.completed" and : > "$DESIGN_TMPDIR/.completed/step-2a" before jumping to Step 2b, while keeping the normal HARD path folded into Step 2a.5

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-resume-routing-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:34-35,76; scripts/design-pause-save.sh:251-263,318; scripts/design-log-publish.sh:294-304,386-403; scripts/design-pause-load.sh:292-296; skills/design/SKILL.md:609-612
- **Concern**: The plan relies on unchanged pause/load, but pause snapshots keep .pause-requested.. Scenario: After the proposed Step 2a fence writes step-1c, step-1d, step-1d.5, and step-1e before the pause-check, design-pause-save publishes the snapshot before removing .pause-requested. design-log-publish includes .pause-requested for --reason pause, and design-pause-load restores it without clearing. Resume can route through 1d.7 via .outline-approved, but Step 2a then immediately sees the restored .pause-requested and pauses again instead of continuing.
- **Proposed resolution**: Keep the routing fold, but add the minimum pause-resume fix: clear .pause-requested after a successful restore in design-pause-load.sh, or exclude it from pause snapshots for --reason pause. Add a focused pause-resume harness case for four discussion sentinels plus .outline-approved so the resume reaches Step 2a once instead of re-pausing.

### FINDING_21:
- **Reviewer(s)**: Cursor-dyn-test-harness-gaps
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:699-764; plan.txt:37-39
- **Concern**: HARD zero-sketch path loses `.completed/step-2a` after fold. Scenario: Item 6 retires the Step 2a success-boundary `: > step-2a` write in favor of the Step 2a.5 prelude host, but the zero-sketch guard still skips Step 2a.5 and jumps to Step 2b; only `step-2a.5` is re-touched at the Step 2b prelude
- **Proposed resolution**: Add an explicit `step-2a` host for that branch (e.g. also write `step-2a` in the Step 2b prelude, or keep a zero-sketch-only sentinel write in the existing no-sketches prose path)

### FINDING_22:
- **Reviewer(s)**: Codex-dyn-test-harness-gaps
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:57-59; scripts/test-design-structure.sh:89-97; skills/design/SKILL.md:1446-1511
- **Concern**: extract_first_bash_fence_after cannot support the proposed design-publish host assertion. Scenario: The helper only returns the first unindented bash fence after a marker. The Step 5c design-publish.sh fence is indented inside a list item, so a naive call after ### 5c skips it and reaches the later Step 6 fence instead; the helper also has no contained-token mode for "fence containing design-publish.sh".
- **Proposed resolution**: Add a small token-containing fence extractor that accepts optional leading spaces on fence delimiters, and use it for step-5b/step-5c; leave extract_first_bash_fence_after for the simple unindented step-anchor hosts.
