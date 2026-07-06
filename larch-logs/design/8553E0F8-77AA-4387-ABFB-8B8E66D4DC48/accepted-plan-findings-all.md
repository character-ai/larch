### FINDING_1: `/design` prompt-contract docs remain stale on the new Step 3 wait contract
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Bg Wait Hook Specialist
- **Severity**: major
- **Concern**: The loaded `/design` contract surfaces are still out of sync on the mid-wait task-output Read and heartbeat-only silent-yield rules, so an orchestrator can keep following stale guidance from `skills/design/SKILL.md`, `AGENTS.md`, or `skills/shared/design-background-wait.md` and either skip the emptiness check or route keepalive-only notifications back into denied probes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/design/SKILL.md: extend NEVER #5 and Step 3 premature-notification contract with (a) one post-notification Read of tasks/*.output to verify emptiness when needed, (b) heartbeat-only KV output silent-yield without sentinel probe while .completed/step-3-terminal is absent, and (c) prefix-identical repeat handling that covers keepalive lines.
  - From Cursor-Arch: Revise design-background-wait.md (and the mirrored SKILL/orchestrator-never contracts) so heartbeat-only STEP3_REVIEW_KEEPALIVE lines with absent .completed/step-3-terminal silent-yield with no probe, same as empty/prefix-identical spurious notifications; reserve sentinel probes for non-keepalive non-empty output only.
  - From Codex-Arch: Add skills/design/SKILL.md to UPDATED and revise the Step 3 notification rules to delegate to the updated shared contract: one task-output Read after notification when needed, empty or heartbeat-only with absent terminal sentinel yields, and only non-heartbeat non-empty output gets the sanctioned probe.
  - From Cursor-Innovation: Add ### UPDATED: skills/design/SKILL.md: extend NEVER #5 ordered steps with one post-notification Read of tasks/*.output to classify empty vs non-empty; add a keepalive-only silent-yield branch before the sentinel probe; update the Step 3 routing table at line 413 to match design-background-wait.md
  - From Cursor-Innovation: Insert an explicit keepalive-only silent-yield step after the emptiness Read and before the sentinel-probe step in both SKILL.md and design-background-wait.md
  - From Cursor-Pragmatic: Add ### UPDATED: skills/design/SKILL.md aligning NEVER #5 and the Step 3 premature-notification table with design-background-wait.md (one post-notification Read of tasks/*.output to confirm emptiness; heartbeat-only non-terminal silent yield; full-output KV scan at completion)
  - From Cursor-Pragmatic: In the AGENTS.md update step, rewrite line 65 to distinguish one post-notification inspection Read during a live wait from polling and from the after-completion parse read
  - From Cursor-Requirements: Reconcile both bullets: permit exactly one post-notification Read of the active tasks/*.output file to verify emptiness before silent yield; keep the no-polling ban for progress polling before notification or between notifications
  - From Cursor-Requirements: Add matching Step 3 and anti-pattern #5 wording: after notification one Read of tasks/*.output may determine emptiness; empty yields silently; heartbeat-only or changed non-empty output follows existing probe or prefix-identical rules
  - From Cursor-dyn-Bg Wait Hook Specialist: Add ### UPDATED: skills/design/SKILL.md: extend anti-pattern #5 and the line-413 contract with (a) one Read of the notified tasks/*.output after <task-notification> to verify emptiness, (b) heartbeat-only output is non-terminal until .completed/step-3-terminal exists, and (c) prefix-identical repeat still applies when output is only keepalive KVs.


### FINDING_2: Shared `orchestrator-never.md` still blocks the new post-notification Read carve-out
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Bg Wait Hook Specialist, Codex-dyn-Bg Wait Hook Specialist
- **Severity**: major
- **Concern**: The shared `skills/shared/orchestrator-never.md` contract remains stale even though AGENTS points readers to it, so secondary readers still get the old pre-notification read ban and the new one-Read-after-notification carve-out is not available everywhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/shared/orchestrator-never.md mirroring the post-notification tasks/*.output Read carve-out and heartbeat-only silent-yield rule; keep Bash/TaskOutput/Monitor bans unchanged.
  - From Cursor-Innovation: Add ### UPDATED: skills/shared/orchestrator-never.md: keep the launch-to-notification ban; add that after a task-notification one Read of the notified tasks/*.output is allowed only to classify empty keepalive-only or terminal output not as progress polling
  - From Codex-Innovation: Add these files to the plan and update only the Step 3 premature-notification wording to allow one post-notification Read of the task output file for emptiness, while preserving the no-polling and no-TaskOutput bans
  - From Codex-Pragmatic: Add skills/shared/orchestrator-never.md to UPDATED files and align NEVER #3/#4 with the new one-read-after-notification carve-out while preserving the no-polling ban
  - From Cursor-Requirements: ### MAY_UPDATE or ### UPDATED orchestrator-never.md: add the same post-notification one-Read emptiness carve-out for /design and update scripts/test-design-structure.sh pins if literal text changes
  - From Codex-Requirements: Add firm updates for skills/design/SKILL.md and skills/shared/orchestrator-never.md so the one post-notification task-output Read exception is consistent across loaded prompt authorities
  - From Cursor-dyn-Bg Wait Hook Specialist: Add ### UPDATED: skills/shared/orchestrator-never.md: after the launch-to-notification ban, state that /design may perform one Read of the notified tasks/*.output only after <task-notification> to distinguish empty spurious output from in-progress keepalive or terminal KVs; TaskOutput, Monitor, Bash probes, and repeated reads remain forbidden.
  - From Codex-dyn-Bg Wait Hook Specialist: Add skills/shared/orchestrator-never.md to firm updates. Narrowly carve out direct Read of the /design task output once after a task notification for empty or heartbeat-only classification; keep Bash reads, TaskOutput, Monitor, repeated reads, result-env reads, and sentinel polling bans.


### FINDING_3: Test coverage and pinned literals still assume the old wait contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-dyn-Bg Wait Hook Specialist
- **Severity**: major
- **Concern**: The verification plan still leaves harnesses and path assumptions pinned to the old behavior: the structure test regexes need updating, and the hook regression assertions must avoid reading from the live marker directory when they intend to validate the carve-out.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: scripts/test-design-structure.sh to assert the new post-notification Read carve-out, heartbeat-only silent-yield wording, and retained probe bans; drop or replace pins that require the old tasks/*.output Read deny story.
  - From Cursor-Innovation: Add ### UPDATED: scripts/test-design-structure.sh (and any touched literals in scripts/test-implement-anti-polling-rule.sh if AGENTS.md wording shifts): refresh pinned substrings for the new post-notification Read carve-out heartbeat-only yield and revised Step 3 ordering
  - From Codex-dyn-Bg Wait Hook Specialist: Change the allow assertions to run from a repo-clone cwd distinct from the marker dir, like the same-clone/subdirectory tests, and keep a separate assertion that Read under the live marker dir still denies. The hook change should remove only the task-output Read arm, not path_under_dir or result/sentinel guards.


### FINDING_5: The keepalive mitigation is under-specified and can still miss the critical silence window
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-Bg Wait Hook Specialist
- **Severity**: major
- **Concern**: The keepalive heartbeat needs a complete lifecycle: it should emit immediately, be stopped and reaped right after the blocking wait finishes, and be covered on cleanup/detach/trap-swap paths so it does not outlive the review or leave the initial silent window unprotected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Start the keepalive helper with one immediate STEP3_REVIEW_KEEPALIVE=waiting printf before entering the sleep loop and document that first emit in design-step3-review.md
  - From Cursor-Pragmatic: In the plan, require stopping and reaping _step3_review_keepalive_pid at the top of _step3_review_cleanup and again before _step3_review_guarantee_post_loop_exit/trap swap; add a detach regression in test-design-step3-review.sh
  - From Cursor-dyn-Bg Wait Hook Specialist: In design-step3-review.sh plan text, require an explicit _step3_review_stop_keepalive call immediately after wait "$_loop_pid" and before trap replacement/normalize-status, with cleanup/detach/signal paths calling the same helper.
  - From Cursor-dyn-Bg Wait Hook Specialist: Document in design-step3-review.md that keepalive is intentionally limited to the primary launch+wait path, or start/stop the same helper around any long wait where wrapper stdout would otherwise stay silent (reattach await included).


### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step3-review.sh:544-564
- **Concern**: [SCOPE-REDUCTION] Fix C keepalive may be unnecessary if Fix A is complete. Scenario: The issue deadlock was hook-blocked emptiness verification. Allowing one post-notification Read plus silent yield fully unblocks that path without a background heartbeat subprocess extra cleanup and stdout-parser churn
- **Proposed resolution**: Consider shipping Fix A plus doc/test updates first and add Fix C only if premature notifications still waste turns after hook unblock


### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step3-review.sh:593-617
- **Concern**: [SCOPE-REDUCTION] The planned Step 3 heartbeat implements Fix C on top of the preferred hook and docs fix. Scenario: Allowing the post-notification Read of tasks/*.output already gives the orchestrator the missing emptiness check, while the heartbeat adds a second stdout writer, new cleanup paths, and new parsing rules that the bug fix does not need
- **Proposed resolution**: Drop the heartbeat helper, heartbeat docs, and heartbeat-specific tests; keep the hook Read carve-out plus the doc contract for one post-notification task-output Read


### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step3-review.sh:2-3
- **Concern**: [SCOPE-REDUCTION] Fix C keepalive is optional once Fix A unblocks tasks/*.output Read for empty-output silent yield. Scenario: Fix A plus doc updates break the denial deadlock; the background keepalive adds trap/cleanup/detach surface and runtime harness cost beyond what the issue requires for correctness
- **Proposed resolution**: State in Approach that Fix C is defense-in-depth for stdout inactivity only; allow shipping A+B first and add C only if live sessions still see premature completed notifications after A


### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-step3-review.sh:592-617
- **Concern**: [SCOPE-REDUCTION] Plan adds a Step 3 stdout heartbeat even though the hook Read carve-out already fixes the reported deadlock. Scenario: The heartbeat changes the task-output contract and can make the final completion output start with repeated keepalive lines, conflicting with the existing first-200-character repeat suppression before terminal KVs are seen
- **Proposed resolution**: Drop Fix C from this PR; keep the hook Read carve-out and documentation updates only


### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:12-19
- **Concern**: [SCOPE-REDUCTION] Step 3 heartbeat adds a second fix path and new lifecycle machinery even though the preferred hook Read exemption plus docs completes the stated bug fix. Scenario: The helper adds a writer process, detach cleanup, stdout parsing changes, and heartbeat-only notification rules; because final output can start with old heartbeat KVs, the first-200 prefix repeat rule can also hide the true completion notification unless more rules are added
- **Proposed resolution**: Drop the heartbeat changes from the firm plan and keep the minimum Fix A plus prompt/docs update path; if heartbeat remains, add explicit completion handling that cannot be suppressed by a stale heartbeat prefix


### FINDING_12:
- **Reviewer(s)**: Codex-dyn-Bg Wait Hook Specialist
- **Severity**: major
- **Focus area**: architecture
- **Location**: plan.txt:3-20,51-59,69-77
- **Concern**: [SCOPE-REDUCTION] Step 3 heartbeat is an extra Fix C implementation on top of the sufficient Fix A task-output Read exemption. Scenario: Once scripts/hook-bg-poll-guard.sh allows direct Read of tasks/*.output and docs explain one post-notification read, the original deadlock is resolved without a new background stdout writer. Keeping the heartbeat adds stdout interleaving and child-cleanup paths to design-step3-review.sh, the exact risks the plan then has to mitigate.
- **Proposed resolution**: Drop plan item 2 and related file/test/doc bullets for heartbeat. Ship the hook Read exemption plus docs/tests. If heartbeat is still desired, split it to a follow-up with its own risk review.


### FINDING_1: Premature-notification contract still blocks the classification Read
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The loaded wait contracts still describe empty-output handling and silent yield in a way that can be read as forbidding the one post-notification `Read` needed to classify a premature notification, and that ambiguity reaches AGENTS.md, skills/design/SKILL.md, skills/shared/design-background-wait.md, and skills/shared/orchestrator-never.md.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "In each listed surface, make step (1) exactly one post-notification Read of the active tasks/*.output; step (2) missing/empty file → silent yield with no further tools; keep prefix-identical repeat and the single sentinel probe after non-empty output; revise silent-yield wording and AGENTS.md "once after completion" so they cover classification Read vs post-completion parse"
  - From Cursor-Innovation: "Reorder every loaded premature-notification contract to: after `<task-notification>`, exactly one Read of the active tasks/*.output to classify; missing/empty file → silent yield; prefix-identical repeat → silent yield; new/changed non-empty file → one terminal-sentinel probe; then after-completion parse. Redefine silent yield as no probe/parse tools after an empty classification Read, not no tools at all"
  - From Cursor-Innovation: "Fix B must state explicitly that empty/non-empty means the tasks/*.output file bytes (missing, whitespace-only, or content), not notification wrapper/summary text; revise AGENTS.md line 65 to distinguish one post-notification emptiness Read from the after-completion result parse; mirror the same wording in orchestrator-never.md NEVER #3"
  - From Cursor-Innovation: "Either extend the listed skills/design/SKILL.md edit to Step 5c/Final summary/Step 4 inline wait bullets, or add one explicit sentence in each that defer to the updated Immediate-background wait rule in skills/shared/design-background-wait.md for post-notification Read classification"
  - From Cursor-Pragmatic: "Rewrite the ordered recovery contract to: (1) after `<task-notification>`, one Read of the active task output; (2) missing/empty file → silent yield with no further tools; (3) prefix-identical repeat → silent yield; (4) new/changed non-empty output → one terminal-sentinel probe. Update NEVER #5 silent-yield wording to forbid further tools after classification, not the classification Read itself; mirror the same ordering in `skills/design/SKILL.md` Step 3 routing and `skills/shared/design-background-wait.md` Step 3 section."
  - From Cursor-Pragmatic: "Revise AGENTS.md:65 to distinguish one post-notification classification Read (not polling; not the after-completion parse) from the after-completion result read, and keep the per-turn no-polling ban otherwise unchanged."
  - From Cursor-Requirements: "Reword silent yield to mean no further tools after the single classification Read; update Apply in order to (0) one post-notification Read of the active tasks/*.output, then (1) empty/missing silent yield, (2) prefix-identical repeat, (3) terminal-sentinel probe; mirror the same ordering in design-background-wait.md Immediate-background and Step 3 sections and refresh both harness pin sets."
  - From Cursor-Pragmatic: "Revise AGENTS.md:65 to distinguish one post-notification classification Read (not polling; not the after-completion parse) from the after-completion result read, and keep the per-turn no-polling ban otherwise unchanged."


### FINDING_2: Anti-polling harness refresh is missing from the plan
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The plan updates the contract prose but leaves `scripts/test-implement-anti-polling-rule.sh` and its test strategy out of scope, so the same pinned literals that enforce the old wait wording will still fail or stay stale in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: "Add `### UPDATED: scripts/test-implement-anti-polling-rule.sh`; refresh the AGENTS.md, design-background-wait.md, and orchestrator-never.md literals so they pin the new one post-notification `Read` carve-out while retaining the no-polling and implement bans."
  - From Cursor-Innovation: "Add scripts/test-implement-anti-polling-rule.sh to the firm plan (or a explicit cross-reference in the test-design-structure item) and refresh pins there in the same change when AGENTS.md and orchestrator-never.md gain the post-notification Read carve-out"
  - From Cursor-Pragmatic: "Add `### UPDATED: scripts/test-implement-anti-polling-rule.sh`, refresh the anchored literals (including `no tool`, empty-output, and Step 3 ordered-routing pins), and run `make test-implement-anti-polling-rule` in Testing strategy."
  - From Codex-Requirements: "Add scripts/test-implement-anti-polling-rule.sh to the plan, refresh its pinned literals for the one-Read-after-notification carve-out, and include make test-implement-anti-polling-rule in focused validation"


