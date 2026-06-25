### OOS_1: [OUT_OF_SCOPE] Stale docs reference retired design-step4b-preview.sh
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `docs/configuration-and-permissions.md` still references the retired `design-step4b-preview.sh` wrapper even though Gate C was retargeted to `design-step3b-tail.sh`, which can mislead future readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Update the doc reference in a follow-up docs pass.


### OOS_2: [OUT_OF_SCOPE] dialectic-protocol Overview still describes removed Step 2a.5 path
- **Reviewer(s)**: dyn-dyn-dialectic-lifecycle-output.txt
- **Severity**: nit
- **Concern**: `skills/shared/dialectic-protocol.md` Overview still describes the removed Step 2a.5 external waterfall and binding `dialectic-resolutions.md` output, which can mislead maintainers about the active Gate C clarifier path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-dialectic-lifecycle-output.txt: Update the Overview section to reflect the active Gate C clarifier path.
```

**Merge notes (brief):**
- **18 in-scope + 2 OOS** blocks from **27** raw inputs.
- Largest merges: raw-pending stale clearing (3), manual `drafter_pick` (3), digest sanitization (3), attribution stripping (2), lifecycle tests (2), structure harness (2).
- **Kept separate:** debater batch `rc` handling, budget timeouts, judge duplicate-vote parsing, manual-vs-auto cache re-entry, generation-aware cache validity, and distinct test-gap findings that target different files or scenarios.
- **OOS blocks** retain `[OUT_OF_SCOPE]` and cite only reviewers whose inputs were exclusively out-of-scope for that item.


