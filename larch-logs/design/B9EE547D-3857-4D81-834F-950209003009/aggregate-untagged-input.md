### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:639-643
- **Concern**: Handoff ~639 terminal-stall prose still authorizes bare `--record-only` while plan scopes macro adoption to post-fence seed/key-rewrite only. Scenario: In current SKILL the ~639 block says "invoke the wrapper with `--record-only`" in prose and then lists seed/key-rewrite before fence ~642; plan line 113 says "Macro adoption replaces only the seed/key-rewrite prose after the fence." That mis-scopes the edit because seed/key-rewrite sits before the fence in file order, not after it. An implementer can leave the prose-level bare `--record-only` invoke, run record-only twice, or omit `--final-round-num` from the prose path even when fence ~642 is correct.
- **Proposed resolution**: Rewrite the UPDATED handoff bullet to replace the whole ~639 terminal-stall conditional: forbid prose-level `invoke ... --record-only`; require a single execution via fence ~642 with both `--final-round-num "$FINAL_ROUND_NUM"` and `--record-only`; then `STALL_TRACKING=true`; then **Durable Bail to Step 18 Macro**. Drop the "after the fence" seed-only scope note and align testing line 182 to the same whole-conditional rewrite.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:639-642
- **Concern**: Handoff terminal-stall edit scoped to post-fence seed/key-rewrite only; pre-fence bare `--record-only` prose survives. Scenario: Plan line 113 limits macro adoption to replacing seed/key-rewrite prose after fence ~642. Current ~639 still says "invoke the wrapper with `--record-only`" without `--final-round-num`. An implementer can follow the plan literally, keep that sentence, and still run a prose-driven `step-5-resume.sh --record-only` (exits 2) before or instead of the fenced invocation with both required flags.
- **Proposed resolution**: Rewrite the entire terminal-stall conditional in the handoff paragraph (~639): one execution path through fence ~642 with `--final-round-num "$FINAL_ROUND_NUM"` and `--record-only` only; then defensive `STALL_TRACKING=true`; then **Durable Bail to Step 18 Macro**. Delete standalone "invoke the wrapper with `--record-only`" prose. Add a testing-strategy grep that ~639 must not contain bare `--record-only` outside the fence line.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:500-695
- **Concern**: Checks Failure Entry Macro call sites lack Rebase-style section-load mandate. Scenario: Rebase post-fence sites require applying routing from `## Rebase Checkpoint Macro` (e.g. SKILL.md:538). The plan shortens fail blockquotes to a compact macro pointer plus site token but never requires loading `## Checks Failure Entry Macro` on `STATUS=fail`. Orchestrators execute the five-line harness window at the fence; a pointer-only blockquote after mandatory `checks-repair-loop.md` read can skip macro post-read routing (`NEXT_ACTION=main-agent-edit`, MAV/coder terminal-stall deferral to handoff ~639, anti-halt). Round-4 neutral finding; plan still omits this.
- **Proposed resolution**: At each five `STATUS=fail` site after the mandatory `checks-repair-loop.md` read, add explicit wording parallel to Rebase: apply orchestrator routing from `## Checks Failure Entry Macro` with the pinned site token. In **Preserved local contract** and **Testing strategy**, grep for that section-load phrase at all five entry sites including the MAV blockquote (~626) outside the harness window.

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:639-642
- **Concern**: Handoff ~639 pre-fence prose still instructs bare `--record-only` while plan limits edits to post-fence seed/key-rewrite. Scenario: Plan line 113 scopes handoff edits to replacing seed/key-rewrite prose after fence ~642 only. Current ~639 text still says "invoke the wrapper with `--record-only`" before that fence. That conflicts with the single execution owner (lines 28-29, 143) and FINDING_4's pinned fence argv. An implementer can add a prompt-side or extra Bash invocation without `--final-round-num`; `step-5-resume.sh` exits 2 and durable bail never runs, or record-only runs twice.
- **Proposed resolution**: In the UPDATED handoff bullet (~111-113), add an explicit edit: rewrite the ~639 terminal-stall sub-clause to remove inline "invoke the wrapper with `--record-only`" wording. State that the sole record-only invocation is fence ~642 with both `--final-round-num "$FINAL_ROUND_NUM"` and `--record-only`, then `STALL_TRACKING=true`, then **Durable Bail to Step 18 Macro**. Add a testing-strategy grep that ~639 prose does not contain bare `--record-only` outside the fence line.
