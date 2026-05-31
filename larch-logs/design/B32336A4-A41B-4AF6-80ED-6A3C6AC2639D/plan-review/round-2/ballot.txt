Reviewing the cited locations to normalize findings and verify merge boundaries.
Four distinct behavioral risks; none describe the same fix or code path, so they stay as four separate findings (no merges).

### FINDING_1: BOTH_DOWN=true drops /review and /research Continue-label split
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: A proposed `BOTH_DOWN=true` interactive sub-branch that only documents **Continue (reduced panel …)** would replace the current Interactive-run bullet that still defers **Continue (degraded waterfall)** / **Continue (degraded)** to each skill for `/review` and `/research`. Orchestrators treating `skills/shared/external-reviewers.md` as canonical could mis-label the consent prompt when both externals are down, even though those skills still run the backup waterfall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: In the BOTH_DOWN=true sub-branch, keep the current split: reduced-panel Continue wording for /design and /implement; defer waterfall/degraded Continue labels to each skill Step 0 bullet for /review and /research (or restate the old line-40 exception verbatim).

### FINDING_2: BOTH_DOWN=false path never sets re-entry sentinel
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Edge-case prose claims a sentinel prevents re-warning on the `BOTH_DOWN=false` path, but the procedure never requires creating it after the notice-only branch. On interactive `BOTH_DOWN=false`, the gate prints a notice and proceeds without `AskUserQuestion`; orchestrators that only touch `.degraded-tools-gate-prompted` after **Continue** can re-run the full gate on `/implement` continue-path re-entry (e.g. resume-plan-tail) and repeat the explanation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add one normative line to the BOTH_DOWN=false interactive sub-branch and mirror in each SKILL.md gate bullet: after printing the notice, create .degraded-tools-gate-prompted (or skip the entire gate when the sentinel already exists)

### FINDING_3: Unspecified BOTH_DOWN fail-safe polarity (empty/unset → auto-proceed risk)
- **Reviewer(s)**: Cursor-dyn-parse-fallback
- **Severity**: important
- **Concern**: Proposed gate prose lists missing/invalid `BOTH_DOWN` in the prompt branch but never names a fail-safe branch polarity. An implementer (or future Bash helper) can map the plan to `if [[ "$BOTH_DOWN" == "true" ]]; then AskUserQuestion; else auto-proceed`, so empty/unparsed `BOTH_DOWN` falls through `else` and auto-proceeds while both externals are down — opposite of Failure modes / parse-fallback intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-parse-fallback: In external-reviewers.md parse step and each SKILL.md gate bullet, state: auto-proceed only when BOTH_DOWN is exactly false; otherwise (true, empty, unset, or not exactly true/false) prompt. Explicitly forbid true-then-else auto-proceed.

### FINDING_4: No CI coverage for missing-BOTH_DOWN parse fallback
- **Reviewer(s)**: Cursor-dyn-parse-fallback
- **Severity**: latent
- **Concern**: No test exercises missing-`BOTH_DOWN` parse fallback on updated skills. After the gate ships `BOTH_DOWN`, `scripts/test-degraded-tools-gate.sh` only asserts emitted `true`/`false`; the partial-deploy / parse-omit path (`DEGRADED=true`, no `BOTH_DOWN` KV) is untested, so fail-safe prose can regress without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-parse-fallback: Add a minimal contract check (e.g. grep that SKILL.md + external-reviewers.md require prompt unless BOTH_DOWN is exactly false) or a synthetic KV fixture test if a parse helper is introduced; detector Cases 2-4/13-14 alone do not cover this
