### FINDING_2: Review-fix waterfall stops at `no-changes` instead of falling through
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan adds Codex→Cursor→Claude as `review.fix_coder` tiers and requires that a successful automated tier with exit 0 but zero working-tree edits fall through to `main-agent-required`, not terminate as `CODER_STATUS=no-changes`. `apply_findings_with_coder` in `python/larch/review/coder_runner.py` (lines 426–431) still returns immediately when any tier succeeds but `_collect_round_stage_paths` is empty. That lets Codex, Cursor, or the new Claude tier stop the waterfall early and mark review-fix complete while accepted findings remain unapplied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `### UPDATED: python/larch/review/coder_runner.py`, change the no-edit branch so non-final automated tiers `continue` and only the last registry tier (or all tiers exhausted) may emit `main-agent-required`; add/adjust `test_review_and_fix.py` for Codex+Cursor fail, Claude success-no-edit → `main-agent-required`.
  - From Cursor-Innovation: In Codex and Cursor fail, Claude launch-claude-review-fix exits 0 without edits, /implement Step 5 or /review review-and-fix reports CODER_STATUS=no-changes instead of escalating, leaving accepted findings unapplied. Add an explicit UPDATED coder_runner.py step: when the Claude tier succeeds with no stage paths, continue the waterfall (do not return no-changes). Prefer handling inside _run_coder_claude or a Claude-only branch; extend test_review_and_fix.py with a Claude no-op fallthrough assertion.
  - From Cursor-Requirements: In `apply_findings_with_coder`, replace the successful `no-changes` early return with `continue` to the next `review.fix_coder` tier (after failed-attempt cleanup), reserving `main-agent-required` for exhaustion of all tiers. Add or adjust `test_review_and_fix.py` waterfall coverage to assert Codex→Cursor→Claude→`main-agent-required` when the last tier succeeds with no edits.


### FINDING_3: Gate B settle path does not restore pre-apply snapshot on dedup failure
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The plan adds a prompt-side pre-apply snapshot for Gate B, but the prompt-side settle path that handles default Gate B apply does not restore that snapshot when gate-b-dedup fails. After inline Gate B rewrites `plan.txt`, a dedup failure before `.gate-b-postapply-ready-N` is written leaves the mutated plan in place and returns `dedup-revise`, so resume can reapply findings or recover from already-mutated bytes instead of the pre-apply plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add skills/design/scripts/design-step35-settle.sh to the plan and restore $DESIGN_TMPDIR/plan-pre-apply-round-$GATE_B_ROUND.txt to plan.txt before returning on Gate B dedup failure, matching _run_dedup restore semantics.


