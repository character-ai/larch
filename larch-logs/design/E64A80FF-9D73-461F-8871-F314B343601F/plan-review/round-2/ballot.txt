Normalized aggregator output from the supplied reviewer findings:

### FINDING_1: Pause checkpoint cannot read `export ISSUE_NUMBER=` from `source-env.sh`
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Edge, Codex-Pragmatic, Codex-Requirements, Codex-dyn-call-site-completeness
- **Severity**: important
- **Concern**: Planned `_postplan_pause_checkpoint` resolves `ISSUE_NUMBER` from `source-env.sh` via `phase_driver_session_get`, but `write-design-current-env.sh` writes `export ISSUE_NUMBER=...` while `phase_driver_session_get` only matches bare `KEY=` lines. If `.pause-requested` appears between EMIT, snapshot, and validator inside the consolidated driver, issue lookup fails and the driver exits 2 instead of execing `design-pause-save.sh`, regressing cooperative pause the extraction is meant to preserve.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch, Codex-Innovation: Resolve the issue from ${ISSUE_NUMBER:-} after the orchestrator prelude, or source/parse source-env.sh using its export format; make the pause harness fixture use export ISSUE_NUMBER=... or generate it through write-design-current-env.sh
  - From Codex-Edge: Have the checkpoint use the already-sourced ISSUE_NUMBER when present or source the generated source-env.sh/read export ISSUE_NUMBER= grammar explicitly; update the pause harness to create source-env.sh with export ISSUE_NUMBER=... rather than a bare KEY= fixture
  - From Codex-Pragmatic: Use inherited ISSUE_NUMBER from the orchestrator prelude first; if absent, source $DESIGN_TMPDIR/source-env.sh or add an explicit export-aware parser. Add the pause harness fixture with export ISSUE_NUMBER=... so this path is covered.
  - From Codex-Requirements: Resolve from inherited ISSUE_NUMBER after the orchestrator prelude, source source-env.sh safely, or extend the helper to parse export KEY= lines. Add the pause harness fixture using the real source-env.sh format.
  - From Codex-dyn-call-site-completeness: Resolve ISSUE_NUMBER from the already-sourced environment first, or source/parse source-env.sh with export syntax support; add the pause harness case using a real write-design-current-env.sh-style source-env.sh.

### FINDING_2: Prose-only re-emit sites omit full postplan driver orchestration handoff
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements, Codex-dyn-kv-contract-coherence
- **Severity**: important
- **Concern**: Plan/reference updates for Gate B shared post-apply and discussion-round2 re-emit swap in `design-postplan-emit.sh` and defects-found routing but omit the Step 2b-equivalent orchestrator contract (canonical prelude, `set +e` capture, file-first `.design-postplan-emit-result.env` parse with symlink guard, exit 2 abort, exit 1 keyed on `POSTPLAN_EMIT_STATUS`). Implementers editing only `approval-gates.md` / `discussion-rounds.md` can leave default `set -e` subshells, parse stdout-only, or skip guards—so exit 1/2 fall through incorrectly, missing-diff-lines repair is skipped, and handoff diverges from Approach / Gate A / Step 5c hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Gate B Shared post-apply and discussion-round2 plan revision are executed from reference prose without a SKILL.md fence; under-specified handoff can let exit 1/2 fall through to Step 2b.5, skip missing-diff-lines repair, or parse stdout-only without the result-env guard Mirror the Step 5c / planned Step 2b block in approval-gates.md steps 7-8 and discussion-rounds.md Plan revision authority: require prelude + set +e driver capture + file-first .design-postplan-emit-result.env parse + exit 2/1 branches before Step 2b.5; or normatively point to the Step 2b driver handoff subsection
  - From Cursor-Requirements: Add to both reference updates the same minimal orchestration block used in SKILL.md Step 2b / Gate A: canonical prelude, set +e driver capture, file-first .design-postplan-emit-result.env read with symlink guard, exit 2 abort, exit 1 branch on POSTPLAN_EMIT_STATUS, then defects-found / Step 2b.5 on exit 0.
  - From Codex-dyn-kv-contract-coherence: Revise the approval-gates.md and discussion-rounds.md entries to require the same .design-postplan-emit-result.env file-first, symlink-refusing parse with stdout fallback, and extend the structure-test pin beyond SKILL.md to all three orchestrator surfaces.

### FINDING_3: Single consolidated driver subshell vs three inline fences (env refresh / pause granularity)
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Driver consolidates three Step 2b subshells into one fence subshell; inter-step checkpoints call `design-pause-save` only and do not re-run the canonical prelude between EMIT, snapshot, and validator. A long `design-postplan-emit.sh` invocation will not pick up env refreshed mid-flight (rare), and pause granularity on resume may differ from three separate fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Document in design-postplan-emit.md that one orchestrator prelude per invocation is intentional; if parity with three fences is required, call _postplan_pause_checkpoint only and keep session re-source out of driver OR accept documented single-subshell semantics in Approach edge cases

### FINDING_4: Stale SKILL.md cross-refs after driver lands (`ACTION=EMIT_PLAN` at re-emit boundaries)
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Concern**: Plan UPDATED scope does not list refreshing Step 2b.5 “Callable from” or Step 3.5 Gate B cross-refs that still name `ACTION=EMIT_PLAN` after the driver lands. Stale normative text can send implementers to reintroduce inline EMIT/validator fences at re-emit boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add grep-backed edits: Step 2b.5 Callable from and Gate B settled-path prose should name design-postplan-emit.sh (keep ACTION=EMIT_PLAN only in shared validator-failure and loop-out-of-scope paths per plan)

### FINDING_5: `missing-diff-lines` collapsed into generic `POSTPLAN_EMIT_STATUS=emit-failed`
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Existing contract repairs `plan.txt` when `EMIT_PLAN_STATUS=missing-diff-lines`. Proposed mapping collapses that case to `POSTPLAN_EMIT_STATUS=emit-failed` while orchestrator branches are keyed on `POSTPLAN_EMIT_STATUS`; call sites that check only the unified status can generic-abort instead of entering the repair path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Either set POSTPLAN_EMIT_STATUS=missing-diff-lines for that case, or require every exit-1 call site to check EMIT_PLAN_STATUS=missing-diff-lines before POSTPLAN_EMIT_STATUS.

### FINDING_6: Unmigrated structure pin still requires `invoke-plan-validator.sh` in `discussion-rounds.md`
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` still pins `discussion-rounds.md` to mention `invoke-plan-validator.sh`. The plan removes the inline validator call from that file, so CI can fail even when driver wiring is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Retarget this pin to design-postplan-emit.sh or include it explicitly in the pin migration list with the other discussion-rounds.md validator pins.

### FINDING_7: discussion-round2 re-emit lacks `review_budget=quick` skip parity
- **Reviewer(s)**: Cursor-dyn-call-site-completeness
- **Severity**: important
- **Concern**: Unified driver applies `review_budget=quick` skip at discussion-round2, but current prose always runs `invoke-plan-validator.sh` with no quick guard. Scope locks no behavior change, yet swapping to the driver without an explicit exception makes quick runs skip validation that today still runs unconditionally at that site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-call-site-completeness: Revise Scope to document intentional quick alignment at discussion-round2 or add an explicit driver/prose exception if parity with current unconditional validation is required

### FINDING_8: Gate A can remain on old inline path while file-level structure tests pass
- **Reviewer(s)**: Codex-dyn-call-site-completeness
- **Severity**: important
- **Concern**: Gate A is a distinct in-scope SKILL.md call site, but planned structure-test migration only requires SKILL.md to mention the new driver somewhere; Step 2b can satisfy that while the Gate A optional-trailer block still retains inline `ACTION=EMIT_PLAN` and `invoke-plan-validator.sh`. The PR can land with three of four prompt-side sites converted despite green structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-call-site-completeness: Add a bounded Gate A assertion in scripts/test-design-structure.sh: locate the Optional trailer guard (Gate A re-entry rewrites) paragraph/block and require design-postplan-emit.sh plus the shared defects-found body/site there; do not rely on a file-level SKILL.md grep.

### FINDING_9: Driver KV contract leaves mandatory keys undefined on several paths
- **Reviewer(s)**: Codex-dyn-kv-contract-coherence
- **Severity**: important
- **Concern**: Proposed driver contract lists mandatory KVs but does not define values for every exit path: `POSTPLAN_EMIT_STATUS` is not set on clean exit 0; not-run/skipped paths leave `DIFF_LINES`, `SNAPSHOT_STATUS`, and `VALIDATE_*` ambiguous. Wrapped helpers today emit subsets only, so result-env can violate the plan’s KV list or leave orchestrator branches reading empty/stale values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-kv-contract-coherence: Add a compact default/status matrix for design-postplan-emit.sh: initialize every listed key before EMIT, set POSTPLAN_EMIT_STATUS=ok on exit-0 success including defects-found/skipped-quick, set explicit not-run/skipped/failed values for snapshot and validator fields, and make the emit-failure POSTPLAN_EMIT_STATUS versus EMIT_PLAN_STATUS branch consistent.
