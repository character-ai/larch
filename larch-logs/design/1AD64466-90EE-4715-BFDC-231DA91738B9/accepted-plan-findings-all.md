### FINDING_1: Inline the full degraded-tools interactive predicate
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The inlined degraded-tools predicate may omit non-interactive cases already covered by the canonical predicate, changing behavior for eval and subagent invocations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Inline the full /implement predicate from skills/shared/external-reviewers.md:37, or state the non-interactive list includes subagents, claude -p, cron, eval, and <<autonomous-loop>> before removing the shared-file load.


### FINDING_2: Honor ROUTE=continue only when the probe exits cleanly
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The conditional rebase-routing skip can mask probe failures if an orchestrator keys only on `ROUTE=continue` and ignores a non-zero probe exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add to each 1.r/4.r/7.r/7a.r routing paragraph: when process rc is non-zero, always read rebase-checkpoint-routing.md regardless of ROUTE; honor ROUTE=continue skip only on rc 0 with ROUTE=continue


### FINDING_3: Add ROUTE KV assertions to the rebase checkpoint probe harness
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The new `ROUTE=` contract is not covered by the existing probe tests, including the non-zero cases called out as a failure mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Extend scripts/test-rebase-checkpoint-probe.sh to assert ROUTE=continue on rc 0 ok/skipped paths, ROUTE=conflict on rc 1, and ROUTE=bail on rc 3 and unexpected-rc paths


### FINDING_4: Remove the remaining runtime pointer to external-reviewers.md
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Step 0 may still mandate reading `skills/shared/external-reviewers.md` at runtime if only the predicate is inlined and the broader procedure pointer remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Replace the external-reviewers.md procedure pointer with a self-contained degraded-gate directive; keep the inlined interactive predicate and existing BOTH_DOWN / sentinel handling in SKILL.md


### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:261
- **Concern**: [SCOPE-REDUCTION] Degraded-gate demotion stops at the interactive-predicate line; line 261 still tells the orchestrator to run the Step 0 procedure in skills/shared/external-reviewers.md. Scenario: The acceptance goal is to stop loading external-reviewers.md on the happy path. Line 261 still names that file as the procedure source, so a faithful orchestrator may load the full shared doc before step-0-degraded-gate.sh even after inlining the predicate at line 269
- **Proposed resolution**: Rewrite the degraded-gate paragraph to anchor the procedure in the existing inline bullets (gate script invocation, DEGRADED/BOTH_DOWN branching, sentinel). Remove the external-reviewers.md load directive entirely; keep only the inlined interactive predicate


### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:56
- **Concern**: [SCOPE-REDUCTION] NEVER #13 compression would delete still-operative guidance. Scenario: #2/#10 are pure retirement stubs; #13 still carries foreground-only ship re-invoke rules (LARCH_SHIP_PR_IMPL selector, no --resume-phase, ship-pr-state read) not duplicated in NEVER #8
- **Proposed resolution**: Keep the one-line removed prefix; retain the operative tail or fold unique bullets into NEVER #8 before stubbing #13




### FINDING_1: Step 0 degraded gate still points at external-reviewers.md
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The Step 0 degraded-gate edit can leave one or both runtime pointers to `skills/shared/external-reviewers.md`, especially the opener around line 261 and the follow-on sentence around line 269, so green-path runs may still load the shared file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace the line 261 opener with inline Step 0 degraded-gate bullets only; drop every `external-reviewers.md` filename from the Step 0 degraded-gate paragraph pair (261 and 269).
  - From Cursor-Innovation: Explicitly require deleting or rewriting line 269 in the SKILL.md edit list; replace with the inlined interactive predicate sentence or fold it into the DEGRADED branching paragraph
  - From Cursor-Pragmatic: Also delete or rewrite the ~269 sentence so it cites only the inlined predicate; grep SKILL.md for external-reviewers.md and confirm zero runtime-load directives remain in Step 0.


### FINDING_4: ROUTE documentation omits required skip and non-zero handling
- **Reviewer(s)**: Cursor-dyn-kv-contract-sync
- **Severity**: important
- **Concern**: The planned `ROUTE` mapping in `scripts/rebase-checkpoint-probe.md` can drift from `SKILL.md` by allowing green-path skips on `rc=0` alone, instead of requiring both `rc=0` and `ROUTE=continue`, and by omitting that any non-zero probe return requires reading the routing reference.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-contract-sync: Align probe.md mapping with SKILL.md: continue skip only when probe rc is 0 and ROUTE=continue; add explicit rule that any non-zero probe rc requires reading rebase-checkpoint-routing.md regardless of ROUTE; mirror edge-case line 79 (ROUTE=continue actionable only with rc 0)




### FINDING_1: Materiality probe still permits unbounded inspection
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: Preflight item 6 still allows open-ended codebase, CLAUDE.md, and AGENTS.md reads before the bounded probe. This can exceed the intended one-tool-call materiality budget.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace the whole materiality instruction with one bounded probe: e.g. run one batched Bash block (plan paths from the issue plus rg/test -f checks), then post stale-notice or continue; drop the separate read codebase preamble
  - From Cursor-Requirements: Replace the whole materiality inspection step with one batched Bash probe block (e.g. existence checks for plan-cited paths) and drop open-ended codebase reads; keep the stale-notice exit-2 path unchanged


### FINDING_2: NEVER #13 migration targets unrelated NEVER #8
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan sends ship re-invoke guidance from NEVER #13 into NEVER #8, which covers ScheduleWakeup and Monitor bans. This can corrupt an unrelated invariant and lose Step 8+ driver recovery details.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Migrate only unique #13 bullets into the existing Step 8+ long-running driver recovery paragraph (~line 782). Stub #13 after parity check. Do not edit NEVER #8 body
  - From Cursor-Pragmatic: Retarget migration to the existing Step 8+ long-running driver recovery prose (~skills/implement/SKILL.md:782); stub #13 only after confirming that block still covers LARCH_SHIP_PR_IMPL bash re-invoke and no --resume-phase


### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-content-migration-fidelity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:46,782; plan.txt:44-47
- **Concern**: [SCOPE-REDUCTION] NEVER #13 migration names NEVER #8 or adjacent but not the Step 8+ blockquote that already holds all four ship re-invoke items. Scenario: Implementer stubs #13 after only touching NEVER #8 generic foreground text and drops bash-path timeout recovery (ship-pr-state read LARCH_SHIP_PR_IMPL selector no --resume-phase)
- **Proposed resolution**: Name skills/implement/SKILL.md:782 as canonical destination; verify four items via grep before stubbing; do not append ship recovery to NEVER #8




### FINDING_1: Preserve uncertain-materiality continue path
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The Preflight item 6 rewrite may remove the current behavior that continues when bounded inspection does not clearly show staleness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: When editing Preflight item 6, keep the bounded single Bash probe as the only inspection step, preserve the stale-notice exit-2 contract unchanged, and add an explicit line: if the probe does not show clear staleness, continue to Step 0 without further codebase or doc reads.


### FINDING_2: Missing ROUTE must not take green-path skip
- **Reviewer(s)**: Codex-dyn-probe-route-completeness
- **Severity**: important
- **Concern**: The rebase-checkpoint green-path skip can incorrectly skip the routing reference when `ROUTE` is missing or malformed, because fallback to existing `REBASE_OUTCOME` routing may silently continue on `rc=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-probe-route-completeness: Replace the missing-ROUTE bullet with: if ROUTE is missing or malformed, read rebase-checkpoint-routing.md, then use the existing REBASE_OUTCOME routing; only rc=0 plus ROUTE=continue skips the read


### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: plan.txt:39-40
- **Concern**: [SCOPE-REDUCTION] Cross-Skill body must not embed the anti-halt harness string. Scenario: test-implement-anti-halt.sh pins the long post-Step-5 line at skills/implement/SKILL.md:589 not inside ### Cross-Skill Presence Propagation
- **Proposed resolution**: Follow the issue sketch: one no-op sentence (e.g. presence unchanged when session flags still true) without pasting the harness phrase



### FINDING_2: Rebase ROUTE contract must replace legacy unconditional and REBASE_OUTCOME routing
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-kv-contract-drift
- **Severity**: important
- **Concern**: Conditional rebase routing may be applied only to the macro header and probe surfaces while stale SKILL.md text still mandates unconditional reference reads or permits `REBASE_OUTCOME` parsing to bypass the `ROUTE=continue` predicate. This can either defeat the token-saving goal on green paths or skip `rebase-checkpoint-routing.md` when `ROUTE` is missing or malformed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace line 143 with the conditional contract (read only on non-zero rc, or rc 0 with ROUTE conflict/bail, or missing/malformed ROUTE; skip only on rc 0 plus ROUTE=continue); do not retain the unconditional MANDATORY sentence
  - From Cursor-dyn-kv-contract-drift: Add an explicit plan step: revise all four post-probe orchestration sentences (~322, ~519, ~704, ~731) to parse `ROUTE=continue|conflict|bail` from probe stdout (or `step-7a.sh` relay), gate reference skip on process rc `0` AND `ROUTE=continue`, and at ~731 state that `Parse REBASE_OUTCOME first` is KV scan ordering within the combined stream (probe relay vs diagram tail), not a substitute for the `ROUTE` skip predicate.



