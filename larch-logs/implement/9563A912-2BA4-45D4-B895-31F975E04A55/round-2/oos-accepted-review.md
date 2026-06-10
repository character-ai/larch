### OOS_3: [OUT_OF_SCOPE] Step 17 masks final-report render failure with exit 0
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-kv-forwarding-output.txt
- **Severity**: latent
- **Concern**: `step-17.sh` logs `write-final-report.sh` failure but falls through with exit 0, contradicting SKILL prose that gates summary emission on a non-zero wrapper exit. The orchestrator may emit a missing or stale `summary-final.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-kv-forwarding-output.txt: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] Unrelated release rebase-sync change bundled with implement refactor
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `.claude/skills/release/SKILL.md` changed in an implement-focused branch, adding scope noise and shipping release behavior without focused tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] Commit telemetry self-rehydration lacks runtime coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-self-rehydration-correctness-output.txt
- **Severity**: important
- **Concern**: The branch moved Step 4/7 telemetry rehydration into commit wrappers, but tests do not fully cover `commit-implementation.sh` and `commit-review-fixes.sh` reading/exporting session-env values. Regressions could silently produce wrong token/timing reports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-self-rehydration-correctness-output.txt: Address the concern above.


### OOS_6: [OUT_OF_SCOPE] Review-fix commit path stages entire worktree
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `commit-review-fixes.sh --stage-all` runs `git add -A` and Step 5 can invoke it automatically, so unrelated untracked files such as `.env` or generated artifacts can be silently committed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


