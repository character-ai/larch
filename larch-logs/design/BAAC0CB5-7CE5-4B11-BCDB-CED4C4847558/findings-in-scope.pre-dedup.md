### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:734-738
- **Concern**: [INCOMPLETE FIX] Gate C long-running debate lacks a normative orchestrator fence contract matching Step 3. Scenario: The plan forbids foreground debate blocking the Step 4 Bash tool (plan.txt:69) and tells `design-step3b-tail.sh` to use immediate-background plus `<task-notification>` (plan.txt:70, 113-116, 341), but `run_in_background` is a Claude Code Bash-tool attribute shells cannot set. `SKILL.md` Step 4 still runs `design-step3b-tail.sh` as a single foreground fence with no raised timeout and no `design-background-wait.md` post-notification sequence, unlike Step 3's explicit `run_in_background: true` / `timeout: 21600000` on `design-step3-review.sh`. A later duplicate block adds `DIALECTIC_GATEC_MODE=background` orchestrator branching (plan.txt:351-354) without wiring it in `SKILL.md`. Implementers can ship sync 300-600s debate inside the foreground tail and hit tool timeout or fail-open cleanup before digest/preview.
- **Proposed resolution**: Pick one owner and document it in `SKILL.md` Step 4: either (A) split into orchestrator fences — sync no-op/cache probe, then `run_in_background: true` + `timeout: 900000` on `design dialectic-gatec` with sentinel wait, then a preview-only tail — or (B) run the whole tail in immediate-background when debate is required, mirroring Step 3. Remove the contradictory instruction that the shell wrapper itself uses immediate-background.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/dialectic-clarifier.md:62-67
- **Concern**: [INCOMPLETE FIX] Late-write generation guard contradicts itself on sidecar enforcement. Scenario: Early normative text says subprocess sidecars do not observe generation and only parent-owned status/digest writers enforce the guard (plan.txt:67). A duplicated later block requires `DIALECTIC_GENERATION` env on subprocess prompts and sidecar collectors that check generation before persisting (plan.txt:339). Implementers can ship parent-only checks while slow sidecars still race after fail-open kill, or add sidecar env plumbing the first section explicitly disclaims.
- **Proposed resolution**: Keep one contract: either parent-only guarded writers (drop sidecar env/check language) or full propagation (name the collector entrypoints and tests). Align `python/design_dialectic.py` and `python/test_design_dialectic.py` to the chosen rule only.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/plan_review.py:1703-1724
- **Concern**: `plan_review.py` clear-stale hook point is unnamed inside the in-loop apply chain. Scenario: The plan requires `dialectic-clear-stale` after the full in-loop apply chain including trailing `gate-b-dedup` and forbids clearing immediately after `revise-waterfall` alone (plan.txt:259-262). It does not name `_run_dedup` / `awaiting-post-apply` as the hook site. `_run_apply` ends at `_run_dedup` (plan_review.py:1817-1818); postplan runs later via `_run_post_apply` (plan_review.py:2404). A hook placed after `revise-waterfall` or before dedup completes can clear valid candidates or miss post-dedup rewrites.
- **Proposed resolution**: Specify: invoke `design dialectic-clear-stale` at successful exit of `_run_dedup` when dedup rc is 0, and rely on `design_postplan.py` for postplan byte changes; do not hook between `revise-waterfall` and dedup.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:732-738
- **Concern**: [ALREADY_ADDRESSED partially] Step 4 orchestrator long-running contract still missing from the primary SKILL.md update block. Scenario: Prior round 4 accepted foreground-tail risk, but the canonical `### UPDATED: skills/design/SKILL.md` section never mirrors Step 3/5c: no `run_in_background: true`, no `timeout: 900000`, and no split-fence when `DIALECTIC_GATEC_MODE=background`. The duplicate appendix (plan.txt:341-354) assigns orchestrator backgrounding, while `design-step3b-tail.sh` bullets (plan.txt:113-116) say the shell wrapper runs "immediate-background" dialectic-gatec, which is a Cursor Bash-tool attribute bash cannot set. Contested-fork runs still hit default Step 4 foreground timeout or fail-open mid-debate.
- **Proposed resolution**: In the primary SKILL.md update, normatively wire Step 4 like Step 3: either (a) raise the Step 4 tail fence to `timeout: 900000` whenever fingerprint-valid auto candidates may debate, or (b) add a two-fence contract (sync probe/no-op, then orchestrator `run_in_background` + wait on `.completed/dialectic-gatec-terminal`, then sync preview tail). Delete the impossible "immediate-background inside design-step3b-tail.sh" wording; keep long-running behavior at orchestrator or Python `--background` + sentinel, not shell prose.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/dialectic-clarifier.md:62-67 vs plan.txt:339-340
- **Concern**: Late-write generation guard contradicts itself on sidecar participation. Scenario: The normative clarifier section says only parent-owned status/digest writers observe generation and subprocess sidecars do not (plan.txt:67). The duplicated appendix requires `DIALECTIC_GENERATION` env and sidecar collectors that check generation before persisting (plan.txt:339-340). Implementers can ship parent-only guards while children still race-write sidecars, or add sidecar plumbing the primary contract explicitly rejects.
- **Proposed resolution**: Keep the cheaper parent-only contract from lines 62-67: delete appendix sidecar env/check language; strip the duplicate block at plan.txt:332-340. Tests should assert status/digest immutability after generation bump, not sidecar collector behavior.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:321-413
- **Concern**: Plan body contains a corrupted duplicate merge block. Scenario: A truncated test bullet ("fingerprint-valid digest## Plan") starts a second pasted copy of SKILL/tail/cli contracts with conflicting tail semantics. Implementers following the appendix can wire DIALECTIC_GATEC_MODE split orchestration while the primary Files section says debate lives entirely inside the tail script.
- **Proposed resolution**: Deduplicate plan.txt before implementation: one canonical contract per surface; move any unique appendix content into the primary `### UPDATED:` sections, then delete lines 321-413.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:755-759
- **Concern**: Step 4b still mandates a second Gate C preview after tail consolidation. Scenario: The primary SKILL.md update says retarget mechanical emit to `design-step3b-tail.sh`, but it does not explicitly remove the Step 4b paragraph that still requires `design-step4b-preview.sh` and, on `--skip-approve`, to "still run the Gate C preview" at 4b. Step 4 tail already runs `plan-review preview --variant gatec` today; leaving 4b prose yields duplicate `## Final Design Plan` emits and violates the cost/context-bloat constraint.
- **Proposed resolution**: In the SKILL.md update, delete the Step 4b "Mechanical Gate C plan emit" paragraph and the `--skip-approve` "still run preview" instruction; Gate C Presentation should consume tail stdout only on the normal path (resume file-read stays narrow per plan).



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:732-738
- **Concern**: [SCOPE-REDUCTION] Step 4 tail long-running contract is specified inside the wrapper but SKILL.md still runs `design-step3b-tail.sh` as a foreground Bash fence with no raised timeout or immediate-background wait.. Scenario: The plan requires up to 300-600s of parallel debater/judge work before Gate C preview (`dialectic-clarifier.md` long-running contract; `design-step3b-tail.sh` must not block on debate). `immediate-background` is an orchestrator Bash-tool flag; a foreground Step 4 fence will still hit the default Bash timeout or fail-open mid-debate on contested-fork runs, violating the issue's cost-discipline and no-new-halt constraints.
- **Proposed resolution**: Update `skills/design/SKILL.md` Step 4 explicitly: when fingerprint-valid candidates exist and `skip_approve_requested=false`, run `design-step3b-tail.sh` with `run_in_background: true` and `timeout` ≥ clarifier budget + slack (≥900s), wait on `<task-notification>` / `.completed/dialectic-gatec-terminal`, then continue to Step 4b; keep sync foreground only for no-candidate/no-debate paths. Add the sentinel to `skills/shared/design-background-wait.md` or document an equivalent probe in the Step 4 fence.



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:755-759
- **Concern**: [ALREADY_ADDRESSED] Gate C mechanical preview retarget is incomplete: Step 4b prose still mandates a separate `design-step4b-preview.sh` emit and tells `--skip-approve` to "still run the Gate C preview" after Step 4 tail already runs preview.. Scenario: Step 4 `design-step3b-tail.sh` already calls `plan-review preview --variant gatec` and writes `.completed/step-4`. Leaving Step 4b instructions unchanged reproduces the round-4 double-emit path (`## Final Design Plan` twice, extra context bloat) despite the plan's tail-only retarget in `approval-gates.md`.
- **Proposed resolution**: In the `skills/design/SKILL.md` Step 4b delta, delete/replace lines 755-759: Gate C mechanical preview and `SKIP_APPROVE_REQUESTED_GATEC` parsing come only from Step 4 tail stdout; Step 4b loads `dialectic-clarifier.md` per deferred-load guard and runs `approval-gates.md` Presentation/Prompt only, with no second `plan-review preview --variant gatec`.



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/dialectic-clarifier.md:62-67
- **Concern**: Late-write generation guard contradicts itself across proposed clarifier text.. Scenario: One normative block says only parent-owned status/digest writers observe `dialectic-clarifier-generation.txt` and subprocess sidecars do not; a duplicated later block requires `DIALECTIC_GENERATION` env on subprocesses and generation checks in sidecar collectors. Implementers can ship the wrong guard and allow post-timeout digest/status mutation after fail-open.
- **Proposed resolution**: Keep the parent-writer-only contract (increment at debate start and again on fail-open; `write_if_generation_matches` on status/digest). Delete the subprocess `DIALECTIC_GENERATION` / sidecar-check language from the plan and tests, or normatively require sidecar collectors to no-op on generation mismatch everywhere (not both).



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py:1771-1773
- **Concern**: `dialectic-clear-stale` hook placement in `plan_review.py` is underspecified for the early dedup-only rewrite path.. Scenario: The plan says clear only after the full apply chain (`revise-waterfall` plus trailing `gate-b-dedup`). `_run_apply` can return after `_run_dedup` alone when `plan.txt` already changed (`awaiting-post-apply` / `postapply_ready`), mutating `plan.txt` without a revise pass in that invocation. A hook only after `revise-waterfall` leaves stale fingerprint-valid candidates until Gate C.
- **Proposed resolution**: Normatively invoke `design dialectic-clear-stale` on every successful `_run_dedup` return (centralize at `_run_dedup` rc=0), or explicitly document and implement the `plan_changed` early-exit at `plan_review.py:1771-1773` as a fourth choke point.



### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:734-738
- **Concern**: [Prior round FINDING_5 incomplete] Step 4 long-running contract still unwired at the orchestrator fence. Scenario: The plan requires immediate-background `dialectic-gatec` with `task-notification` wait and `.completed/dialectic-gatec-terminal` (plan lines 69-70, 353-354), but assigns that behavior to `design-step3b-tail.sh` internals. `SKILL.md` Step 4 still invokes the tail as a single foreground Bash fence with no `run_in_background: true`, no raised timeout, and no split-fence choreography. A synchronous `python3 … design dialectic-gatec` inside the shell script still blocks the Bash tool for 300-600s, matching failure mode 10 and violating the hard no-context-bloat / no-extra-halt cost constraint. `skills/shared/design-background-wait.md` also omits the new terminal sentinel.
- **Proposed resolution**: Add normative `SKILL.md` Step 4 wiring: either run the full tail with `run_in_background: true` and `timeout: 900000` when debate may be required, or split Step 4 into sync rejected-findings + immediate-background `dialectic-gatec` + sync preview with explicit wait rules. Update `design-background-wait.md` to register `.completed/dialectic-gatec-terminal` and post-notification parsing. Remove orchestrator-only `task-notification` language from the shell wrapper contract unless the orchestrator owns the wait.



### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/dialectic-clarifier.md:62-67
- **Concern**: Late-write generation guard contradicts duplicated appendix contract. Scenario: Normative `dialectic-clarifier.md` text says subprocess sidecars do not observe generation and only parent-owned status/digest writers enforce the guard (line 67). A duplicated appendix block (lines 339-340) adds `DIALECTIC_GENERATION` env and sidecar collector checks. Implementers can ship incompatible guards; slow child sidecars may still mutate artifacts after fail-open despite the stated mitigation.
- **Proposed resolution**: Pick one contract in `dialectic-clarifier.md` and `design_dialectic.py`: parent-only generation-guarded writers (delete lines 339-340 and sidecar env), or explicit subprocess generation env with collector checks (delete line 67 parent-only claim). Drop the duplicate appendix merge so one normative section remains.



### FINDING_14:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:227-233
- **Concern**: Drafter dialectic candidates may be retained only in an in-process DrafterParseResult. Scenario: Step 2b launches the Codex or Claude drafter through separate agent launcher processes, then design_lifecycle.py runs postplan in the parent process. If parse_drafter_output only retains valid dialectic JSON in DrafterParseResult, that payload is lost before post-postplan promotion, so the primary self-declared fork path never writes dialectic-clarifier-candidates.json for Gate C.
- **Proposed resolution**: Make the transient raw candidate sidecar mandatory across the process boundary. Write $DESIGN_TMPDIR/.dialectic-raw-pending.json from the drafter launcher after parse validation, have dialectic-promote-candidates consume an explicit --raw-dialectic-file after POSTPLAN_RC=0, and clear the sidecar at Step 2b start and after promotion.



### FINDING_15:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-step3b-tail.sh:113-116
- **Concern**: Gate C long-running debate is assigned to an impossible inner immediate-background handoff. Scenario: The Step 4 Bash tool call invokes design-step3b-tail.sh. That shell script cannot set the host Bash tool's run_in_background flag after inspecting DIALECTIC_GATEC_MODE. If it backgrounds and waits internally, the outer Bash tool still foreground-blocks for the debate budget. If it prints the mode and exits, preview ordering and digest emission break.
- **Proposed resolution**: Move the immediate-background boundary to the prompt-side SKILL.md Step 4 call path, or make the whole Step 4 tail fence the backgrounded tool with a clear terminal contract. Do not require design-step3b-tail.sh itself to invoke Bash-tool immediate-background mode.



