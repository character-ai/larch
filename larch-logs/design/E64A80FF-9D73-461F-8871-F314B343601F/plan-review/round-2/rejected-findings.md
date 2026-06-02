### [Plan Review] FINDING_2

### FINDING_2: Prose-only re-emit sites omit full postplan driver orchestration handoff
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements, Codex-dyn-kv-contract-coherence
- **Severity**: important
- **Concern**: Plan/reference updates for Gate B shared post-apply and discussion-round2 re-emit swap in `design-postplan-emit.sh` and defects-found routing but omit the Step 2b-equivalent orchestrator contract (canonical prelude, `set +e` capture, file-first `.design-postplan-emit-result.env` parse with symlink guard, exit 2 abort, exit 1 keyed on `POSTPLAN_EMIT_STATUS`). Implementers editing only `approval-gates.md` / `discussion-rounds.md` can leave default `set -e` subshells, parse stdout-only, or skip guards—so exit 1/2 fall through incorrectly, missing-diff-lines repair is skipped, and handoff diverges from Approach / Gate A / Step 5c hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Gate B Shared post-apply and discussion-round2 plan revision are executed from reference prose without a SKILL.md fence; under-specified handoff can let exit 1/2 fall through to Step 2b.5, skip missing-diff-lines repair, or parse stdout-only without the result-env guard Mirror the Step 5c / planned Step 2b block in approval-gates.md steps 7-8 and discussion-rounds.md Plan revision authority: require prelude + set +e driver capture + file-first .design-postplan-emit-result.env parse + exit 2/1 branches before Step 2b.5; or normatively point to the Step 2b driver handoff subsection
  - From Cursor-Requirements: Add to both reference updates the same minimal orchestration block used in SKILL.md Step 2b / Gate A: canonical prelude, set +e driver capture, file-first .design-postplan-emit-result.env read with symlink guard, exit 2 abort, exit 1 branch on POSTPLAN_EMIT_STATUS, then defects-found / Step 2b.5 on exit 0.
  - From Codex-dyn-kv-contract-coherence: Revise the approval-gates.md and discussion-rounds.md entries to require the same .design-postplan-emit-result.env file-first, symlink-refusing parse with stdout fallback, and extend the structure-test pin beyond SKILL.md to all three orchestrator surfaces.


### [Plan Review] FINDING_3

### FINDING_3: Single consolidated driver subshell vs three inline fences (env refresh / pause granularity)
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Driver consolidates three Step 2b subshells into one fence subshell; inter-step checkpoints call `design-pause-save` only and do not re-run the canonical prelude between EMIT, snapshot, and validator. A long `design-postplan-emit.sh` invocation will not pick up env refreshed mid-flight (rare), and pause granularity on resume may differ from three separate fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Document in design-postplan-emit.md that one orchestrator prelude per invocation is intentional; if parity with three fences is required, call _postplan_pause_checkpoint only and keep session re-source out of driver OR accept documented single-subshell semantics in Approach edge cases


