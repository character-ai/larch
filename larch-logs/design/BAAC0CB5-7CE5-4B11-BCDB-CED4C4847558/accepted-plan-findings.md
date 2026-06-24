### FINDING_1: Step 4 orchestrator lacks normative long-running / background fence contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Codex-Generic
- **Severity**: blocking
- **Concern**: The plan forbids foreground debate blocking the Step 4 Bash tool and assigns immediate-background `dialectic-gatec` with `<task-notification>` wait to `design-step3b-tail.sh`, but `run_in_background` is a Claude Code Bash-tool attribute shells cannot set. `SKILL.md` Step 4 still invokes the tail as a single foreground fence with no raised timeout and no `design-background-wait.md` post-notification sequence (unlike Step 3's explicit `run_in_background: true` / `timeout: 21600000`). A duplicate appendix adds `DIALECTIC_GATEC_MODE=background` orchestrator branching without wiring it in the primary `SKILL.md` update. Implementers can ship sync 300–600s debate inside the foreground tail, hit tool timeout, or fail-open cleanup before digest/preview; contested-fork runs violate the hard no-context-bloat / no-extra-halt cost constraint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pick one owner and document it in `SKILL.md` Step 4: either (A) split into orchestrator fences — sync no-op/cache probe, then `run_in_background: true` + `timeout: 900000` on `design dialectic-gatec` with sentinel wait, then a preview-only tail — or (B) run the whole tail in immediate-background when debate is required, mirroring Step 3. Remove the contradictory instruction that the shell wrapper itself uses immediate-background.
  - From Cursor-Innovation: In the primary SKILL.md update, normatively wire Step 4 like Step 3: either (a) raise the Step 4 tail fence to `timeout: 900000` whenever fingerprint-valid auto candidates may debate, or (b) add a two-fence contract (sync probe/no-op, then orchestrator `run_in_background` + wait on `.completed/dialectic-gatec-terminal`, then sync preview tail). Delete the impossible "immediate-background inside design-step3b-tail.sh" wording; keep long-running behavior at orchestrator or Python `--background` + sentinel, not shell prose.
  - From Cursor-Requirements: Add normative `SKILL.md` Step 4 wiring: either run the full tail with `run_in_background: true` and `timeout: 900000` when debate may be required, or split Step 4 into sync rejected-findings + immediate-background `dialectic-gatec` + sync preview with explicit wait rules. Update `design-background-wait.md` to register `.completed/dialectic-gatec-terminal` and post-notification parsing. Remove orchestrator-only `task-notification` language from the shell wrapper contract unless the orchestrator owns the wait.
  - From Codex-Generic: Move the immediate-background boundary to the prompt-side SKILL.md Step 4 call path, or make the whole Step 4 tail fence the backgrounded tool with a clear terminal contract. Do not require design-step3b-tail.sh itself to invoke Bash-tool immediate-background mode.


### FINDING_2: Late-write generation guard contradicts itself on sidecar participation
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Early normative text says subprocess sidecars do not observe generation and only parent-owned status/digest writers enforce the guard; a duplicated later block requires `DIALECTIC_GENERATION` env on subprocess prompts and sidecar collectors that check generation before persisting. Implementers can ship parent-only checks while slow sidecars still race after fail-open kill, or add sidecar env plumbing the first section explicitly disclaims.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep one contract: either parent-only guarded writers (drop sidecar env/check language) or full propagation (name the collector entrypoints and tests). Align `python/design_dialectic.py` and `python/test_design_dialectic.py` to the chosen rule only.
  - From Cursor-Innovation: Keep the cheaper parent-only contract from lines 62-67: delete appendix sidecar env/check language; strip the duplicate block at plan.txt:332-340. Tests should assert status/digest immutability after generation bump, not sidecar collector behavior.
  - From Cursor-Pragmatic: Keep the parent-writer-only contract (increment at debate start and again on fail-open; `write_if_generation_matches` on status/digest). Delete the subprocess `DIALECTIC_GENERATION` / sidecar-check language from the plan and tests, or normatively require sidecar collectors to no-op on generation mismatch everywhere (not both).
  - From Cursor-Requirements: Pick one contract in `dialectic-clarifier.md` and `design_dialectic.py`: parent-only generation-guarded writers (delete lines 339-340 and sidecar env), or explicit subprocess generation env with collector checks (delete line 67 parent-only claim). Drop the duplicate appendix merge so one normative section remains.


### FINDING_3: `dialectic-clear-stale` hook site underspecified in `plan_review.py` apply chain
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan requires `dialectic-clear-stale` after the full in-loop apply chain including trailing `gate-b-dedup` and forbids clearing immediately after `revise-waterfall` alone, but does not name `_run_dedup` / `awaiting-post-apply` as the hook site. `_run_apply` ends at `_run_dedup`; postplan runs later via `_run_post_apply`. A hook placed after `revise-waterfall` or before dedup completes can clear valid candidates or miss post-dedup rewrites. Additionally, `_run_apply` can return after `_run_dedup` alone when `plan.txt` already changed (`awaiting-post-apply` / `postapply_ready`), mutating `plan.txt` without a revise pass in that invocation; a hook only after `revise-waterfall` leaves stale fingerprint-valid candidates until Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify: invoke `design dialectic-clear-stale` at successful exit of `_run_dedup` when dedup rc is 0, and rely on `design_postplan.py` for postplan byte changes; do not hook between `revise-waterfall` and dedup.
  - From Cursor-Pragmatic: Normatively invoke `design dialectic-clear-stale` on every successful `_run_dedup` return (centralize at `_run_dedup` rc=0), or explicitly document and implement the `plan_changed` early-exit at `plan_review.py:1771-1773` as a fourth choke point.


### FINDING_4: Plan body contains corrupted duplicate merge block
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: A truncated test bullet ("fingerprint-valid digest## Plan") starts a second pasted copy of SKILL/tail/cli contracts with conflicting tail semantics. Implementers following the appendix can wire `DIALECTIC_GATEC_MODE` split orchestration while the primary Files section says debate lives entirely inside the tail script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Deduplicate plan.txt before implementation: one canonical contract per surface; move any unique appendix content into the primary `### UPDATED:` sections, then delete lines 321-413.


### FINDING_6: Drafter dialectic candidates may be lost across process boundary
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Step 2b launches the Codex or Claude drafter through separate agent launcher processes, then `design_lifecycle.py` runs postplan in the parent process. If `parse_drafter_output` only retains valid dialectic JSON in `DrafterParseResult`, that payload is lost before post-postplan promotion, so the primary self-declared fork path never writes `dialectic-clarifier-candidates.json` for Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Make the transient raw candidate sidecar mandatory across the process boundary. Write $DESIGN_TMPDIR/.dialectic-raw-pending.json from the drafter launcher after parse validation, have dialectic-promote-candidates consume an explicit --raw-dialectic-file after POSTPLAN_RC=0, and clear the sidecar at Step 2b start and after promotion.


### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:732-738
- **Concern**: [SCOPE-REDUCTION] Step 4 tail long-running contract is specified inside the wrapper but SKILL.md still runs `design-step3b-tail.sh` as a foreground Bash fence with no raised timeout or immediate-background wait.. Scenario: The plan requires up to 300-600s of parallel debater/judge work before Gate C preview (`dialectic-clarifier.md` long-running contract; `design-step3b-tail.sh` must not block on debate). `immediate-background` is an orchestrator Bash-tool flag; a foreground Step 4 fence will still hit the default Bash timeout or fail-open mid-debate on contested-fork runs, violating the issue's cost-discipline and no-new-halt constraints.
- **Proposed resolution**: Update `skills/design/SKILL.md` Step 4 explicitly: when fingerprint-valid candidates exist and `skip_approve_requested=false`, run `design-step3b-tail.sh` with `run_in_background: true` and `timeout` ≥ clarifier budget + slack (≥900s), wait on `<task-notification>` / `.completed/dialectic-gatec-terminal`, then continue to Step 4b; keep sync foreground only for no-candidate/no-debate paths. Add the sentinel to `skills/shared/design-background-wait.md` or document an equivalent probe in the Step 4 fence.


