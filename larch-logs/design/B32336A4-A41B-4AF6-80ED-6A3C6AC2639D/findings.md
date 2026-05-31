### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/shared/external-reviewers.md:38-41
- **Concern**: Proposed BOTH_DOWN=true interactive branch drops the existing /review and /research Continue-label exception. Scenario: The plan replaces the current Interactive-run bullet (which defers **Continue (degraded waterfall)** / **Continue (degraded)** to each skill) with a single BOTH_DOWN=true sub-branch that only names **Continue (reduced panel …)**. Orchestrators that treat this section as canonical can mis-label the consent prompt on /review and /research when both externals are down, even though those skills still run the backup waterfall.
- **Proposed resolution**: In the BOTH_DOWN=true sub-branch, keep the current split: reduced-panel Continue wording for /design and /implement; defer waterfall/degraded Continue labels to each skill Step 0 bullet for /review and /research (or restate the old line-40 exception verbatim).

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/external-reviewers.md:43
- **Concern**: Edge case claims sentinel prevents re-warn on BOTH_DOWN=false path but procedure never requires it. Scenario: Interactive BOTH_DOWN=false prints notice and proceeds without AskUserQuestion; orchestrators that only touch .degraded-tools-gate-prompted after Continue will re-run the gate on /implement continue-path re-entry (e.g. resume-plan-tail) and repeat the full explanation
- **Proposed resolution**: Add one normative line to the BOTH_DOWN=false interactive sub-branch and mirror in each SKILL.md gate bullet: after printing the notice, create .degraded-tools-gate-prompted (or skip the entire gate when the sentinel already exists)

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-parse-fallback
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/external-reviewers.md:35-40; skills/design/SKILL.md:200; skills/implement/SKILL.md:455; skills/research/SKILL.md:139; skills/review/SKILL.md:29
- **Concern**: Proposed gate prose lists missing/invalid BOTH_DOWN in the prompt branch but never names a fail-safe branch polarity. Scenario: An implementer (or future Bash helper) can map the plan to if [[ "$BOTH_DOWN" == "true" ]]; then AskUserQuestion; else auto-proceed. Empty/unparsed BOTH_DOWN falls through else and auto-proceeds while both externals are down — opposite of Failure modes / parse-fallback intent
- **Proposed resolution**: In external-reviewers.md parse step and each SKILL.md gate bullet, state: auto-proceed only when BOTH_DOWN is exactly false; otherwise (true, empty, unset, or not exactly true/false) prompt. Explicitly forbid true-then-else auto-proceed.

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-parse-fallback
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-degraded-tools-gate.sh:52-80; plan Testing strategy (lines 131-134)
- **Concern**: No test exercises missing-BOTH_DOWN parse fallback on updated skills. Scenario: After gate ships BOTH_DOWN, test-degraded-tools-gate.sh only asserts emitted true/false; partial-deploy / parse-omit path (DEGRADED=true, no BOTH_DOWN KV) is untested — fail-safe prose can regress without CI signal
- **Proposed resolution**: Add a minimal contract check (e.g. grep that SKILL.md + external-reviewers.md require prompt unless BOTH_DOWN is exactly false) or a synthetic KV fixture test if a parse helper is introduced; detector Cases 2-4/13-14 alone do not cover this
