# Review Round 5

- Mode: `diff`
- 8 accepted, 11 rejected (6 neutral)

## Accepted Findings

### FINDING_1: Stale pause-save sentinel can skip resumed wrapper phases
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: `.pause-save-complete` is durable across resume. Combined wrappers can treat stale pause state as current completion and skip Step 3 preview, Gate C read, or Step 6 cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Clear .pause-save-complete during pause load or at wrapper entry after resume; do not treat a stale marker as terminal success.
  - From codex-specialist-correctness-output.txt: Use a per-invocation sentinel, clear stale state before child calls, delete after consuming, or return a dedicated pause status.
  - From codex-specialist-testing-output.txt: Use an invocation-scoped sentinel, clear it at wrapper entry, or return an explicit pause status from child wrappers.
  - From dyn-risk-integration-output.txt: Clear `.pause-save-complete` at the start of each combined wrapper (or in `design-pause-load.sh` / resume env refresh), and add `test-design-pause-resume.sh` cases that pause mid-`design-step3-entry.sh` / `design-step4b.sh` / `design-step6.sh` and assert the second phase runs after resume.
  - From dyn-risk-integration-output.txt: Extend the pin to all three combined wrappers and add lifecycle tests that assert sentinel creation, consumption, and clearing.


### FINDING_10: Step 0 remains split across consecutive wrapper fences
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: Step 0 still runs parse, session, degraded, route, and init as separate fences. The linter allows heading-only boundaries, so the planned phase-aware single-wrapper or real prompt-boundary invariant is not enforced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Collapse Step 0 into design-step0.sh phases or tighten the no-consecutive-fence invariant to require real prompt-side boundaries.
  - From codex-specialist-testing-output.txt: Merge no-boundary Step 0 calls or require real prompt-side boundaries, then tighten scripts/test-design-structure.sh so headings do not satisfy the boundary check.
  - From dyn-architecture-output.txt: Add `design-step0.md` contracts per sub-script (or a shared Step 0 contract doc), behavioral tests for parse-before-setup, verbal issue binding, and optional merge back into fewer entrypoints if turn reduction remains a goal.


### FINDING_14: Route state sidecar sources unquoted issue title
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `.design-step0-route-state.env` writes untrusted `ISSUE_TITLE` as raw shell syntax before init sources it. Titles with spaces can abort init, and crafted titles can execute shell syntax.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Quote all sidecar values safely or read them through read-result-env.sh with an allowlist instead of sourcing raw output.
  - From codex-specialist-testing-output.txt: Write the sidecar with shell-safe quoting or parse it via read-result-env.sh, and add a regression for spaces and shell metacharacters.


### FINDING_15: Verbal issue creation is not handed back to route
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: After `/larch:issue` creates an issue, the next Step 0 route wrapper has no issue-number argument. Verbal `/design` can abort with `POSITIONAL_KIND=verbal` and empty `ISSUE_NUMBER`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Add a resume/verbal route argument such as --issue-number and persist it safely before route.
  - From dyn-architecture-output.txt: Add `--issue-number` to `design-step0-route.sh`, document the verbal path in `SKILL.md`, and pin verbal routing in `test-design-structure.sh` (or restore a small resume wrapper).


### FINDING_2: Missing or malformed BOTH_DOWN can auto-proceed degraded mode
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `design-step0-degraded.sh` defaults or branches on `BOTH_DOWN` too loosely. Missing, empty, or malformed gate output can proceed as one-tool-down or non-interactive both-down instead of requiring the degraded decision path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Track BOTH_DOWN parse presence; treat missing/malformed BOTH_DOWN as needs-degraded-decision, not one-down.
  - From cursor-specialist-correctness-output.txt: Restrict degraded-both-down-auto to BOTH_DOWN=true exactly; fail closed on empty/unset/malformed values.
  - From codex-specialist-correctness-output.txt: Track whether BOTH_DOWN was seen and accept only exact false for one-down and exact true for non-interactive both-down.
  - From cursor-specialist-edge-cases-output.txt: Restrict non-interactive auto-proceed to BOTH_DOWN=true exactly; fail closed or emit needs-degraded-decision otherwise.
  - From codex-specialist-edge-cases-output.txt: Only auto-proceed on exact false or exact true in the intended branches, and send unset or malformed values to needs-degraded-decision.
  - From dyn-architecture-output.txt: Track whether `BOTH_DOWN` was parsed; treat unset/malformed like both-down for branching; pin gate stdout fixtures in the harness.


### FINDING_3: Sketch collector waits on paths that were never launched
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `sketch-launched-paths.txt` is read but not written. Collection falls back to availability flags, so launch failures can make the collector wait on unlaunched output paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Persist launched slot paths at sketch launch and pass them into design-step2a3-collect.sh.
  - From cursor-specialist-edge-cases-output.txt: Pass launched paths via -- or write sketch-launched-paths.txt at launch; remove silent availability fallback.


### FINDING_4: Step 4 completion sentinel is written before Gate C read completes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `design-step4b.sh` writes `step-4` before preview and read are complete. Resume after pause can skip `SKIP_APPROVE_REQUESTED_GATEC` emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Defer step-4 write until preview+read complete, or force read retry after resume.


### FINDING_9: Postplan status handoff is incomplete for rc 12 and 13
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `design-step2b-postplan.sh` writes only `step-2b` on some branches. Missing `step-2b.5` and structured status can make pause/resume re-enter the wrong state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Emit POSTPLAN_RC and POSTPLAN_STATUS for every rc and write step-2b plus step-2b.5 only in explicit terminal continue wrappers.


