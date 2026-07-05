### OOS_1: [OUT_OF_SCOPE] Frontmatter and catalog copy must mention the merit gate
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-oos-merit
- **Severity**: important
- **Concern**: The skill metadata and mirrored catalog entries still describe actuality-only behavior, so operators who read the frontmatter or docs may miss the merit gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Rewrite the description blurb to mention actuality plus merit and sync the mirrored catalog entries
  - From dyn-dyn-oos-merit: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] blocked_sources.json must be rebuilt after rescues
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-oos-merit
- **Severity**: important
- **Concern**: Post-rescue regrouping can leave the blocked-source set stale, so a source that still has unresolved merit can be treated as closable or eligible for `oos-5` on the old prompt-side state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add explicit blocked_sources rebuild before oos-5 apply, forbid empty default when merit_pending sources exist, and hard-gate --source-issues against any source with pending merit items
  - From codex-specialist-edge-cases: Regenerate blocked_sources.json after merit confirmation and rescues, or make close-eligible consume the final post-rescue proposal state instead of the stale pre-approval file.

### OOS_3: [OUT_OF_SCOPE] Stale Python path comment
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: A maintainer comment points to an outdated Python path, which can mislead future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Update comment to python/larch/issue/combine_issues.py

### OOS_4: [OUT_OF_SCOPE] merit_pending close-eligible path lacks a pin test
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: The close-eligible path lacks a test that pins the new `merit_pending` blocking behavior, so a prompt-side omission could slip through CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a close-eligible test with reason merit_pending

