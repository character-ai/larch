### OOS_1: [OUT_OF_SCOPE] Harness lacks pre-fence load-contract ordering checks
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `context_after` in `scripts/test-implement-anti-polling-rule.sh` (74–90) only validates post-fence proximity of shared-ref strings, so pre-fence load-contract ordering regressions are not CI-gated. Ordering bugs like FINDING_1 can land while all harness assertions still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Extend the harness with pre-fence ordering checks once SKILL.md load blocks are moved above fences.

---


