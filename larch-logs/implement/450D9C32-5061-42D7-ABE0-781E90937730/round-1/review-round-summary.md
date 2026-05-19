# Review Round 1

- Mode: `diff`
- Accepted findings: 10
- Rejected findings: 4
- Exonerated findings: 0
- Neutral findings: 2

## Accepted Findings

### FINDING_1: **Important** `risk-integration` `scripts/test-ship-pr.sh:652`, `scripts/test-ship-pr.sh:777` — The ship-pr harness still asserts the removed post-create push and removed `pr_number` manifest update. With the new `scripts/ship-pr.sh:951-1008` flow, `git-push.sh` is no longer called after PR creation and `larch-log.sh manifest --field pr_number=...` is gone, so `make test-ship-pr-postmerge` will fail these assertions. Update the harness to expect the pre-PR `larch-log.sh commit`, no post-create push, no `pr_number` manifest write, and add coverage that a post-create `write-final-report.sh` failure records a warning without stalling.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/test-ship-pr.sh:652`, `scripts/test-ship-pr.sh:777` — The ship-pr harness still asserts the removed post-create push and removed `pr_number` manifest update. With the new `scripts/ship-pr.sh:951-1008` flow, `git-push.sh` is no longer called after PR creation and `larch-log.sh manifest --field pr_number=...` is gone, so `make test-ship-pr-postmerge` will fail these assertions. Update the harness to expect the pre-PR `larch-log.sh commit`, no post-create push, no `pr_number` manifest write, and add coverage that a post-create `write-final-report.sh` failure records a warning without stalling.
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: docs/run-logs.md:229-231
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] 'Written at Step 18' unchanged while content describes earlier pr-create placeholder and canonical URL in comment. Doc readers assume no final-summary activity until Step 18 despite ship-pr doing pre-create writes. Update timing line to cover Step 8+ pr-create and Step 18 (or say marker may update multiple times).
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/implement/SKILL.md:1680
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 7a prose still says the first larch:final-summary projection is written immediately after PR_NUMBER/PR_URL persist, but ship-pr now runs write-final-report before PR creation with placeholder PR fields. Operators or automation assume no final-summary tracking upsert until after PR_URL exists, or mis-order audits relative to the real two-phase GitHub comment updates. Reword to reflect two upserts (pre-PR placeholder vs post-persist live URL) or remove the incorrect first/immediately-after clause.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: skills/implement/SKILL.md:1680
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Contradictory prose: claims first deterministic larch:final-summary after PR_NUMBER/PR_URL persist while also describing pre-create placeholder write. Readers mis-order API upserts vs state_set_many and mis-debug when tracking comment shows N/A before create. Rewrite clause so first upsert pre-create placeholder vs post-state_set live URL is explicit and ordered.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: skills/implement/SKILL.md:1680
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Stale clause claims first larch:final-summary projection happens immediately after ship-pr persists PR_NUMBER/PR_URL while ship-pr.sh now invokes write-final-report.sh before create-pr and before state_set_many. Operators or tooling authors rely on Step 7a prose for ordering and mis-model when placeholder vs live PR URL exists or when the tracking-issue comment is first updated. Reword or delete the stale clause so the paragraph matches scripts/ship-pr.sh run_pr_create_phase (~951-1008): pre-create write with placeholder PR fields optional pre-PR larch-log commit then post-create best-effort API refresh.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: scripts/ship-pr.sh:999-1008 skills/implement/scripts/write-final-report.sh:68-79
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Post-create write-final-report.sh rewrites tracked larch-logs/.../final-summary.md on disk without a commit after the pre-PR commit froze PR:N/A. After a successful pr-create phase, git status shows a modified tracked final-summary.md; dirty-tree guards or clean-tree expectations can false-positive. Make the post pass API-only (new flag), or restore the committed file after upsert, or split helpers so the second pass does not mutate the log tree.
- **Suggested revision**: Address the concern above.


### FINDING_2: **Nit** `code-quality` `skills/implement/SKILL.md:1680` — The updated prose still says the first deterministic `larch:final-summary` projection is written after `ship-pr.sh` persists `PR_NUMBER`/`PR_URL`, but the new script writes the committed placeholder summary before `create-pr.sh`. Reword this to distinguish the pre-PR committed placeholder from the post-create API-only tracking comment refresh.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `code-quality` `skills/implement/SKILL.md:1680` — The updated prose still says the first deterministic `larch:final-summary` projection is written after `ship-pr.sh` persists `PR_NUMBER`/`PR_URL`, but the new script writes the committed placeholder summary before `create-pr.sh`. Reword this to distinguish the pre-PR committed placeholder from the post-create API-only tracking comment refresh.
- **Suggested revision**: Address the concern above.


### FINDING_3: **Nit** `risk-integration` `docs/run-logs.md:229` — The section still says `larch:final-summary` is written at Step 18, while the new behavior also writes it during PR creation with placeholder PR fields. Update the timing sentence so the canonical run-log docs match the new PR-create placeholder plus later live-comment refresh behavior.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 3. **Nit** `risk-integration` `docs/run-logs.md:229` — The section still says `larch:final-summary` is written at Step 18, while the new behavior also writes it during PR creation with placeholder PR fields. Update the timing sentence so the canonical run-log docs match the new PR-create placeholder plus later live-comment refresh behavior.
- **Suggested revision**: Address the concern above.


### FINDING_4: **Nit** `risk-integration` `scripts/ship-pr.md:70`, `scripts/ship-pr.md:95-98` — The ship-pr helper contract still documents the deleted `pr_number` manifest update and post-create log-refresh push. Bring this file in sync with `scripts/ship-pr.sh:951-1008`: pre-PR final-summary commit rides on `create-pr.sh`’s push, and the post-create refresh is API-only.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 4. **Nit** `risk-integration` `scripts/ship-pr.md:70`, `scripts/ship-pr.md:95-98` — The ship-pr helper contract still documents the deleted `pr_number` manifest update and post-create log-refresh push. Bring this file in sync with `scripts/ship-pr.sh:951-1008`: pre-PR final-summary commit rides on `create-pr.sh`’s push, and the post-create refresh is API-only. I could not run the harness in this read-only sandbox; `mktemp` failed with `Operation not permitted`.
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: skills/implement/SKILL.md:1680
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 7a prose still says first larch:final-summary projection happens immediately after PR_NUMBER PR_URL persist. Contradicts new pre-create placeholder final-summary and pre-PR log commit; misleads orchestrators about when PR URL appears on disk versus tracking issue. Remove or rewrite the stale sentence so a single accurate timeline remains.
- **Suggested revision**: Address the concern above.


