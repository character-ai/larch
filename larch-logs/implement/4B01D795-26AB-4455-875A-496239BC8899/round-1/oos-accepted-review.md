### OOS_1: [OUT_OF_SCOPE] Stale voter manifest can leak across review rounds
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_fresh_design_voter_manifest` can treat a prior round’s root `plan-voter-slots.ndjson` as current because freshness is not anchored to the current `round_dir` or round start floor. This can show stale voter progress and a premature “round complete; plan vote in progress” header during the next round’s panel review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Empty voter manifest hides Claude-only voting progress
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When external voters are unavailable, an empty `plan-voter-slots.ndjson` can suppress the voter-phase header even while Claude voting is active. Claude voter progress should be counted independently from external manifest lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] Vote branch can declare round complete before reviewers finish
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The voter branch can print “round N complete; plan vote in progress” without verifying reviewer `returned == total`, producing contradictory output such as `reviewers: 1/3` beside a round-complete label.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] Round 2+ auto-continuation step matching loses voter detail
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Multi-round plan review auto-continuation timing marks may not match `_is_design_plan_review_step`, causing the renderer to fall back to generic progress output without voter detail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


