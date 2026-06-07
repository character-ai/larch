### OOS_1:
- **Description**: [OUT_OF_SCOPE] Ledger could read review-round-count.txt inside reviewer-prune.sh instead of argv threading. Scenario: Adding run-step3-review → plan-review-loop → dispatch round plumbing is correct but widens the call chain; the counter already lives in $DESIGN_TMPDIR/review-round-count.txt at filter time.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/run-step3-review.sh:137-137
- **Phase**: design

### OOS_2:
- **Description**: skills/review/SKILL.md:48. Scenario: Plan updates /review SKILL for pruning but not heavy-worker.md, which still documents a 3-round safety limit while the wrapper uses round_cap=5
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/references/heavy-worker.md:36
- **Phase**: design

