### OOS_1: OOS disposition harness fixtures assume every vote-accepted OOS is filed
- **Description**: OOS disposition harness fixtures assume every vote-accepted OOS is filed. Scenario: Once OOS_ACCEPTED_COUNT and accepted sinks mean fileable-only, this large harness will likely fail until fixtures distinguish vote-accepted vs fileable accepted. Track as follow-up test refresh; not required for core gate correctness if unit tests cover tally and serialize.
- **Reviewer**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-oos-disposition-gate.sh
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/6423
### OOS_2: Legacy latent-reroute markers still branch on body **Severity**: latent after latent is retired
- **Description**: Legacy latent-reroute markers still branch on body **Severity**: latent after latent is retired. Scenario: With reviewer emit-cut and nit drops, new runs should not produce latent body severities; keeping latent-reroute adds dead branches and confuses classification versus judge nit drops
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/larch/review/review_tally.py:635-660
- **Phase**: design




### OOS_3: plan-mode prune-nit-findings --oos-file path becomes dead code after drop-not-move semantics
- **Description**: plan-mode prune-nit-findings --oos-file path becomes dead code after drop-not-move semantics. Scenario: Production callers use --input-mode code only; plan mode still implements move-to-oos_file renumbering that the plan retires but never references in plan_review_round.py
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/review/review_aggregate.py:1028-1067
- **Phase**: design




### OOS_6: Progress summaries may still treat `OOS_ACCEPTED_COUNT` as all vote-accepted
- **Description**: Progress summaries may still treat `OOS_ACCEPTED_COUNT` as all vote-accepted. Scenario: If the counter becomes fileable-only, operator-facing progress text can overstate how many OOS items will file
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/larch/report/progress_report.py:141-175
- **Phase**: design




### OOS_7: #6028 dropped-OOS final-summary interaction not spelled out
- **Description**: #6028 dropped-OOS final-summary interaction not spelled out. Scenario: Scope anchor asks reconciling #6028 with silent dropped `nit`; plan only documents audit lineage and hides rejected OOS, not dropped-nit visibility
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/run-logs.md:453
- **Phase**: design




### OOS_8: run-log projection not updated for revived oos-dropped-before-vote.md
- **Description**: run-log projection not updated for revived oos-dropped-before-vote.md. Scenario: round artifact allowlist currently excludes oos-dropped-before-vote.md so dropped-nit audit lineage stays session-local and /fluff-analysis cannot see it from committed logs
- **Reviewer**: Cursor-dyn-Review Pipeline Gate
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/report/run_log_batch.py:450-453
- **Phase**: design

### OOS_4: Operator voting docs still describe every vote-accepted non-security OOS as filed
- **Description**: Operator voting docs still describe every vote-accepted non-security OOS as filed. Scenario: After the file gate lands, `docs/voting-process.md` will still tell operators that accepted non-security OOS is filed, with no strict-majority-`major` requirement
- **Reviewer**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/voting-process.md:118-124
- **Phase**: design




