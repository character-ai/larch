### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:81,413; skills/shared/design-background-wait.md:15,29; AGENTS.md:64-65
- **Concern**: Fix B names a post-notification tasks/*.output Read but the planned doc edits do not reorder the premature-notification contract or fix the "silent yield means no tool" rule that forbids it. Scenario: Loaded text still starts with "(1) empty output → silent yield" and defines silent yield as zero tool calls, so an orchestrator cannot legally perform the new classification Read; it keeps probing sentinels or guessing emptiness and the Step 3 denial loop can persist even after the hook unblocks Read
- **Proposed resolution**: In each listed surface, make step (1) exactly one post-notification Read of the active tasks/*.output; step (2) missing/empty file → silent yield with no further tools; keep prefix-identical repeat and the single sentinel probe after non-empty output; revise silent-yield wording and AGENTS.md "once after completion" so they cover classification Read vs post-completion parse



### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-implement-anti-polling-rule.sh:178-183
- **Concern**: Plan updates AGENTS.md and shared wait docs but omits this CI-pinned anti-polling harness, which still asserts the old no-read wording.. Scenario: The planned doc changes can make `make test-implement-anti-polling-rule` fail even though the feature works, leaving the PR unverifiable in CI.
- **Proposed resolution**: Add `### UPDATED: scripts/test-implement-anti-polling-rule.sh`; refresh the AGENTS.md, design-background-wait.md, and orchestrator-never.md literals so they pin the new one post-notification `Read` carve-out while retaining the no-polling and implement bans.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:81,413; skills/shared/design-background-wwait.md:15
- **Concern**: Premature-notification ordered contract still classifies empty output before any Read step. Scenario: After Fix A the hook allows tasks/*.output Read, but NEVER #5, Step 3 routing, and the Immediate-background wait rule still say (1) empty output → silent yield and silent yield means call no tool before explaining how emptiness is determined; orchestrators can keep probing sentinels on premature notifications whose wrapper text is non-empty while the output file is still empty (the live failure mode)
- **Proposed resolution**: Reorder every loaded premature-notification contract to: after `<task-notification>`, exactly one Read of the active tasks/*.output to classify; missing/empty file → silent yield; prefix-identical repeat → silent yield; new/changed non-empty file → one terminal-sentinel probe; then after-completion parse. Redefine silent yield as no probe/parse tools after an empty classification Read, not no tools at all



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: AGENTS.md:64-65; skills/shared/orchestrator-never.md:9
- **Concern**: Loaded contracts still equate empty/non-empty with notification text or ban all task-output Reads before completion. Scenario: AGENTS.md line 64 probes on non-empty task output while line 65 says Read the task output once after completion; design-background-wait leads with non-empty premature output → probe; the bug report had a non-empty `<task-notification>` summary with an empty tasks/*.output file, so docs can still route to denied sentinel probes without the classification Read
- **Proposed resolution**: Fix B must state explicitly that empty/non-empty means the tasks/*.output file bytes (missing, whitespace-only, or content), not notification wrapper/summary text; revise AGENTS.md line 65 to distinguish one post-notification emptiness Read from the after-completion result parse; mirror the same wording in orchestrator-never.md NEVER #3



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-anti-polling-rule.sh:178-186
- **Concern**: Plan refreshes design structure pins but not the implement anti-polling harness that pins the same AGENTS.md/orchestrator-never wait literals. Scenario: Only scripts/test-design-structure.sh is listed; scripts/test-implement-anti-polling-rule.sh also substring-pins AGENTS.md polling/empty-output clauses and orchestrator-never.md recovery text, so a partial doc edit can pass design structure CI while leaving implement anti-polling stale or failing once line 64-65/orchestrator-never wording changes
- **Proposed resolution**: Add scripts/test-implement-anti-polling-rule.sh to the firm plan (or a explicit cross-reference in the test-design-structure item) and refresh pins there in the same change when AGENTS.md and orchestrator-never.md gain the post-notification Read carve-out



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:622
- **Concern**: Step 5c (and other non-Step-3 bg waits) keep inline premature-notification rules without the new Read carve-out. Scenario: Plan Fix B names Step 3 in skills/design/SKILL.md updates but Step 5c still says empty output yields silently and probe only after new/changed non-empty premature output without the one-Read classification step; Step 5c uses the same immediate-background pattern and the same hook, so the same premature-notification deadlock can recur outside Step 3
- **Proposed resolution**: Either extend the listed skills/design/SKILL.md edit to Step 5c/Final summary/Step 4 inline wait bullets, or add one explicit sentence in each that defer to the updated Immediate-background wait rule in skills/shared/design-background-wait.md for post-notification Read classification



### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:7-15
- **Concern**: [SCOPE-REDUCTION] The Read carve-out is specified for every live bg wait even though the bug is /design Step 3 only. Scenario: The plan would remove the task-output Read deny globally and word the contract generically, which weakens the existing /implement Steps 3/5 notification-only guard that says not to read task output while the child is still running. A premature /implement notification could now read empty task output each turn and revive the polling loop the hook currently blocks.
- **Proposed resolution**: Scope Fix A/B to /design Step 3. In the hook, exempt task-output Read only when the retained live marker step is design-step3-review. Keep task-output Read denial for implement markers. Word AGENTS.md and orchestrator-never.md as a /design-only carve-out while preserving /implement notification-only text.



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: code-quality
- **Location**: scripts/test-implement-anti-polling-rule.sh
- **Concern**: Fix B omits the second anti-polling harness that pins the same wait-contract literals. Scenario: Fix B only lists `scripts/test-design-structure.sh` for literal refresh and `make test-design-structure` in testing, but `scripts/test-implement-anti-polling-rule.sh` also pins `skills/shared/design-background-wait.md`, `skills/design/SKILL.md` anti-pattern #5, and `AGENTS.md` recovery prose via `check_context` anchors (`After the background launch ack`, `5. **NEVER act on empty-output`, Step 3 ordered routing). Rewording for the post-notification classification Read will break those anchored checks on `test-harnesses-5` even when `test-design-structure` passes.
- **Proposed resolution**: Add `### UPDATED: scripts/test-implement-anti-polling-rule.sh`, refresh the anchored literals (including `no tool`, empty-output, and Step 3 ordered-routing pins), and run `make test-implement-anti-polling-rule` in Testing strategy.



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:81,413; skills/shared/design-background-wait.md:15,29; skills/shared/orchestrator-never.md:9
- **Concern**: Loaded contracts still say silent yield means no tool before emptiness is verified. Scenario: Fix A only unblocks hook reads; current NEVER #5, immediate-wait, Step 3, and orchestrator-never text still tell the orchestrator to treat empty output as silent yield with no tool calls and to avoid task-output reads before a confirmed sentinel. Without an explicit first step (one post-notification Read of the active `tasks/*.output` to classify empty vs non-empty), models can keep probing sentinels and re-hit the denial loop despite the hook change.
- **Proposed resolution**: Rewrite the ordered recovery contract to: (1) after `<task-notification>`, one Read of the active task output; (2) missing/empty file → silent yield with no further tools; (3) prefix-identical repeat → silent yield; (4) new/changed non-empty output → one terminal-sentinel probe. Update NEVER #5 silent-yield wording to forbid further tools after classification, not the classification Read itself; mirror the same ordering in `skills/design/SKILL.md` Step 3 routing and `skills/shared/design-background-wait.md` Step 3 section.



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: AGENTS.md:65
- **Concern**: Second AGENTS polling bullet still reads as forbid-all-reads-until-completion. Scenario: The plan revises the long bg-wait bullet but not the separate `Do not poll the task output file once per turn... Read the task output once, after completion` line. That line can be read as banning the new mid-wait classification Read and push orchestrators back toward sentinel probes on premature notifications.
- **Proposed resolution**: Revise AGENTS.md:65 to distinguish one post-notification classification Read (not polling; not the after-completion parse) from the after-completion result read, and keep the per-turn no-polling ban otherwise unchanged.



### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: scripts/hook-bg-poll-guard.sh:1128-1154
- **Concern**: [SCOPE-REDUCTION] The planned Read carve-out removes the global tasks/*.output denial for every live marker, not just /design recovery. Scenario: An implement-step5-review or implement-step3-checks marker currently denies same-clone Read of tasks/foo.output while the child is still running; after deleting the arm, that Read is allowed even though skills/implement/SKILL.md and orchestrator-never keep /implement premature notifications notification-only and forbid task-output reads, reopening the polling path the hook protects.
- **Proposed resolution**: Scope the Read exemption to the /design wait steps that need empty-output classification, or keep tasks/*.output Read denied for implement-* markers and keep/update the implement marker regression assertions



### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-anti-polling-rule.sh
- **Concern**: The plan updates contract prose in AGENTS.md, skills/design/SKILL.md, skills/shared/design-background-wait.md, and skills/shared/orchestrator-never.md but only lists scripts/test-design-structure.sh for pinned-literal refresh and runs only make test-design-structure in Testing strategy. test-implement-anti-polling-rule.sh separately pins the same surfaces (for example the Step 3 ordered premature-notification literal at line 571 and check_context anchor windows for Empty output / no tool within two lines of After the background launch ack). Doc edits without matching harness updates will fail make test-implement-anti-polling-rule on CI harness shard test-harnesses-5 even when test-design-structure passes.. Scenario: Add scripts/test-implement-anti-polling-rule.sh under Files to modify/create, refresh the Step 3 routing and design-background-wait anchor literals for the post-notification classification Read ordering, and run make test-implement-anti-polling-rule in Testing strategy alongside make test-design-structure.
- **Proposed resolution**: 



### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: AGENTS.md:65
- **Concern**: AGENTS.md still has a second bullet: Do not poll the task output file once per turn while a run_in_background task runs. Read the task output once, after completion. The plan only calls for revising the preceding bg-wait bullet (~line 64). The new Fix B contract requires exactly one Read of tasks/*.output after a premature notification and before true completion to classify empty output. Leaving line 65 unchanged tells orchestrators that any pre-completion task-output Read is forbidden, so they can skip the classification Read and remain unable to apply empty-output silent yield during live Step 3 waits.. Scenario: Reconcile or merge the line-65 bullet with Fix B: allow one post-notification Read of the active task output for emptiness classification only; keep the ban on per-turn polling and on repeated reads; distinguish that carve-out from the after-completion parse.
- **Proposed resolution**: 



### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:81
- **Concern**: skills/shared/design-background-wait.md:15-29. Scenario: Loaded contracts still define silent yield as call no tool (SKILL anti-pattern #5: Silent yield means call no tool; design-background-wait Step 3: Take no action: call no tool) and order checks as (1) empty output silent yield before any mechanism to learn emptiness. Fix B requires one post-notification Read before that branch, but the plan does not explicitly require rewording the silent-yield definition or inserting a prerequisite step in the ordered contract. An implementer can add hook allowance while leaving call no tool intact, and orchestrators will still skip the classification Read and reproduce the deadlock.
- **Proposed resolution**: Reword silent yield to mean no further tools after the single classification Read; update Apply in order to (0) one post-notification Read of the active tasks/*.output, then (1) empty/missing silent yield, (2) prefix-identical repeat, (3) terminal-sentinel probe; mirror the same ordering in design-background-wait.md Immediate-background and Step 3 sections and refresh both harness pin sets.



### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-implement-anti-polling-rule.sh:179-207
- **Concern**: Prior pin-refresh fix is incomplete; this CI harness also pins the old empty-output-first Step 3 wait wording and is not listed in the plan. Scenario: The plan revises AGENTS.md, skills/design/SKILL.md, design-background-wait.md, and orchestrator-never.md to add the one post-notification Read carve-out, but make lint/test-harnesses-3 can still fail on this unchanged harness or leave the new contract unpinned here
- **Proposed resolution**: Add scripts/test-implement-anti-polling-rule.sh to the plan, refresh its pinned literals for the one-Read-after-notification carve-out, and include make test-implement-anti-polling-rule in focused validation



