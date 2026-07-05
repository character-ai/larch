### OOS_1: [OUT_OF_SCOPE] Legacy Step 5b file-issues dispatch can still surface a prompt
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-oos-autofile
- **Severity**: latent
- **Concern**: The legacy Step 5b `file-issues` dispatch still does not carry an explicit no-confirmation / AskUserQuestion ban, so old-transcript or manual-repair readers can still treat filing as operator-gated before `/larch:issue`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-oos-autofile: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Implement pre-driver still lacks a prompt-side no-confirmation contract
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-oos-autofile
- **Severity**: important
- **Concern**: The active `/implement` pre-driver still routes through `python/cli.py oos file` without a prompt-side no-confirmation rule, so the normal implement path can still ask for confirmation even if the legacy `oos-pipeline.md` reference was updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-oos-autofile: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] finalize-step5 prose was over-condensed
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The diff condenses unrelated `finalize-step5` prose beyond the contract literals, which increases review noise and removes text that no harness pins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Empty-stdout retry ownership is split
- **Reviewer(s)**: dyn-dyn-oos-autofile
- **Severity**: important
- **Concern**: The empty-stdout retry prose and `design_step5b.py` disagree on when `.oos-issue-retry-used` is written, so an orchestrator can hit an existing sentinel and skip the documented retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-autofile: Address the concern above.

