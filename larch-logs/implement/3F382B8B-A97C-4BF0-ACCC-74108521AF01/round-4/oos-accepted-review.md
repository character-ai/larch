### OOS_17: [OUT_OF_SCOPE] Security OOS detector misses bold Focus area field
- **Reviewer(s)**: codex-specialist-security-output.txt
- **Severity**: important
- **Concern**: The security OOS detector may fail to hold accepted OOS blocks using the documented `- **Focus area**: security` form, allowing security OOS material into public artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Recognize the documented bold Focus area field in is_security_block and add a regression fixture using the exact accepted OOS template.


### OOS_18: [OUT_OF_SCOPE] Single-important continuation threshold diverges from `/implement`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-stateflow-output.txt, dyn-artifacts-output.txt, dyn-contracts-output.txt
- **Severity**: important
- **Concern**: The continuation predicate fires on one important/high finding (`HIGH_ACCEPTED_COUNT > 0`) while the referenced `/implement` heuristic and issue plan use `important-accepted >= 2`, increasing automatic rounds and cost for small otherwise-converged changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use HIGH_ACCEPTED_COUNT >= 2 and add harness coverage for the boundary.
  - From cursor-specialist-correctness-output.txt: Add test-plan-review-continuation cases or extend test-step3-review-cap.sh.
  - From dyn-stateflow-output.txt: Align the predicate with `/implement` (`HIGH_ACCEPTED_COUNT >= 2`, optionally plus plan-size/`diff_lines` analogues), or document the asymmetry as a deliberate `/design` policy and add a harness case for the 1-important-finding stop/continue boundary.
  - From dyn-contracts-output.txt: Align thresholds with `/implement` (at minimum `HIGH_ACCEPTED_COUNT >= 2`), add an accepted-count ≥ 8 continue path, and replace plan-metadata “structural” with a post–Gate-B delta signal (e.g., `diff_lines` / `diff_added` delta after apply) closer to `structural_loc >= 100`; update `SKILL.md`, `plan-review-continuation.md`, and `test-step3-review-cap.sh` together.


### OOS_19: [OUT_OF_SCOPE] Automatic continuation deletes prior round snapshots
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-stateflow-output.txt, dyn-contracts-output.txt
- **Severity**: latent
- **Concern**: Each Step 3 re-entry removes prior `plan-review/round-*` directories, so multi-round runs lose per-round forensic artifacts even though cumulative accepted findings survive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Consider preserving round dirs on auto-continuation or snapshot before delete.
  - From dyn-stateflow-output.txt: Stop wholesale `rm -rf` of prior `plan-review/round-N/` trees on auto-continuation entry (only remove the upcoming round slot), or snapshot rounds to monotonically numbered directories that are never deleted until design publish.


