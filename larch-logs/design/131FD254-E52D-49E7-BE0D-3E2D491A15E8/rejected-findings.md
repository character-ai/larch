### [Plan Review] FINDING_16

### FINDING_16: Threshold guard should reject 0 too
- **Concern**: The `case "$_summary_threshold" in (''|*[!0-9]*)` pattern accepts `0`. A 0 threshold makes every plan summarize (since `wc -l` is always ≥ 0), which silently hides all plan content. Latent UX issue.
- **Proposed resolution**: Treat `0` as invalid: extend the pattern to `case "$_summary_threshold" in (''|0|*[!0-9]*) _summary_threshold=120 ;; esac`. Folded into FINDING_2's proposed resolution.


### [Plan Review] FINDING_4

### FINDING_4: Step 3 large-plan opt-in is not actionable before reviewer launch
- **Concern**: The plan's Step 3 entry bold note tells users they can "ask to see the full plan if you wish" before voting begins. But Step 3 has no AskUserQuestion before reviewers launch — the orchestrator immediately proceeds to scout + dispatch under the anti-halt rule. A user reading a large-plan summary cannot reliably interrupt to request the full plan before 10+ reviewers begin reading the plan. Four reviewers (Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Requirements) flagged this.
- **Proposed resolution**: When the Step 3 entry summary mode fires (plan exceeds threshold), add a small **blocking** AskUserQuestion with exactly two options: **Begin review** (proceed to scout/dispatch with summary already displayed) and **Show full plan first** (orchestrator emits full `plan.txt` content under a `## Full Plan Candidate` header, then re-fires the same two-option prompt). The prompt fires ONLY when summary mode fires; small plans skip the prompt. Note: this prompt is at Step 3 entry only, not at Gate C — Gate C already has a 3-option AskUserQuestion that the user can answer with `Other` to request the full plan.


### [Plan Review] FINDING_7

### FINDING_7: touch exit status not checked
- **Concern**: `touch "$DESIGN_TMPDIR/.step3-entry-plan-printed"` is unconditional. Transient FS or permission errors silently leave no sentinel; every Step 3 re-entry re-prints the entire plan candidate (or the summary). This is latent — `touch` failures are rare but the cost of failure is high (re-print spam).
- **Proposed resolution**: Capture the `touch` exit status; on failure, print `**⚠ 3: sentinel write failed (touch exit N); plan candidate may re-print on Step 3 re-entry**` and continue. Document the fallback in the plan's Edge cases.


