### OOS_1: [OUT_OF_SCOPE] Stale pre-driver SKILL.md references legacy disposition-checkpoint path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/SKILL.md` pre-driver prose still tells orchestrators the Python path runs `python/cli.py oos disposition-checkpoint` after `oos file`, while NEVER #14/#15 restrict checkpoint bookkeeping to `implement step-8-oos-checkpoint` on the post-`/issue` path. That can confuse resumptions and reintroduce prompt-side checkpoint fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Rephrase the pre-driver bullet to describe only `oos file` pre-ship behavior, and point post-pipeline disposition to the new checkpoint verb.


### OOS_2: [OUT_OF_SCOPE] Transient retry counter not reset after successful ship completion
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `ship-pr-net-retries-python.count` is never reset after `NEXT_ACTION=complete` or non-transient `reship`. A later exit-6 episode in the same `$IMPLEMENT_TMPDIR` can hit the stall cap sooner than four fresh transient failures (e.g., count already 3 on re-entry).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reset the count file on exit 0 `complete` (and optionally on non-transient `reship`).


### OOS_3: [OUT_OF_SCOPE] NEVER #5 still references legacy disposition-checkpoint exit contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: NEVER #5 (`skills/implement/SKILL.md:40`) still points at `python/cli.py oos disposition-checkpoint` exit 0 for the legacy bash path, while NEVER #14/#15 center `implement step-8-oos-checkpoint`. Low risk of operator confusion from the stale cross-reference.


### OOS_4: [OUT_OF_SCOPE] Structure harness pins NEVER #14 but not NEVER #15
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Plan-required NEVER #15 structure pin is absent (`scripts/test-implement-structure.sh:384-385`); only NEVER #14 is pinned. A revert of the #15 `OOS_PENDING` clearing contract would not fail the structure harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a require() pin for the rewritten NEVER #15 prose about checkpoint-only OOS_PENDING clearing.


