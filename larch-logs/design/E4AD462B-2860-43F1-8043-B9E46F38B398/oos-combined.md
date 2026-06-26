### OOS_1: [OUT_OF_SCOPE] Parent audit copy never clears stale `oos-dropped-before-vote.md` when a later round has no drops.
- **Description**: [OUT_OF_SCOPE] Parent audit copy never clears stale `oos-dropped-before-vote.md` when a later round has no drops.. Scenario: After one round writes dropped OOS and a later round drops nothing, the parent-side audit file still shows the old content. Downstream readers can mistake a prior round’s OOS set for the current run.
- **Reviewer**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:1933-1940,2247-2264
- **Phase**: design
