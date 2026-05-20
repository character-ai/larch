### [rejected] FINDING_1

### FINDING_1: **correctness** — [`skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh`](skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh) `233-249` (`active-session-keeps-version`): nine seeded dirs `29.1.20`–`29.1.28`, install `29.1.30` → ten dirs; `LATEST_STABLE` `29.1.30`; pins/executing protect `29.1.21`; removable oldest are `29.1.20` then `29.1.22`; eight kept (`21`, `23`–`28`, `30`). Arithmetic matches assertions.
- **Reviewer**: dyn-test-case-arithmetic-output.txt
- **Concern**: - **correctness** — [`skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh`](skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh) `233-249` (`active-session-keeps-version`): nine seeded dirs `29.1.20`–`29.1.28`, install `29.1.30` → ten dirs; `LATEST_STABLE` `29.1.30`; pins/executing protect `29.1.21`; removable oldest are `29.1.20` then `29.1.22`; eight kept (`21`, `23`–`28`, `30`). Arithmetic matches assertions.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_10

### FINDING_10: `b282bfeb` — chore(larch-logs): flush implement run DF68EB95-09BD-4B74-BBD1-A23B7B218CD9  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `b282bfeb` — chore(larch-logs): flush implement run DF68EB95-09BD-4B74-BBD1-A23B7B218CD9
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_11

### FINDING_11: `d4d4370f` — Address code review feedback (round 1)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `d4d4370f` — Address code review feedback (round 1) Reviewed the precomputed diff at `<TMPDIR>/round-2/diff.txt` (plus a quick read of the current [`upgrade-larch.sh`](skills/upgrade-larch/scripts/upgrade-larch.sh) prune helpers for how `version` is sourced).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_13

### FINDING_13: architecture: skills/upgrade-larch/scripts/upgrade-larch.md:18
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] §8 gains new “pins do not consume prune budget” contract language not listed in plan doc edits. Doc/plan checklist misaligned for reviewers tracing only the written plan. Add matching bullet to the plan or trim doc to plan-specified edits only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

### FINDING_14: code-quality: skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh (multi-pinned-oldest-still-trims-to-eight); skills/upgrade-larch/scripts/test-upgrade-larch-prune.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Extra harness + doc coverage beyond the plan's single new cap-prune case name Minor plan/traceability drift for issue-driven workflows Align plan or issue text with the added multi-pin regression
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

### FINDING_15: code-quality: skills/upgrade-larch/scripts/upgrade-larch.md:18
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] 'Each session-derived pin emits…' understates executing-root preservation in the same bullet Readers may think only session-env pins are warned or preserved for cap pruning Clarify session-env vs executing-root pins and when stderr warnings fire
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

### FINDING_17: code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh:295 vs skills/upgrade-larch/scripts/upgrade-larch.sh:323-324
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Two different preservation warning strings for related prune skips Inconsistent operator-facing diagnostics Unify messages via helper with reason, or document intentional difference
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

### FINDING_2: **correctness** — `no-sessions-keeps-under-cap` / `unparseable-session-keeps-under-cap` ([`skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh`](skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh) `251-278`): four dirs after install, below cap 8; expecting all four kept is consistent with `VERSION_COUNT > KEEP_LIMIT` being false.
- **Reviewer**: dyn-test-case-arithmetic-output.txt
- **Concern**: - **correctness** — `no-sessions-keeps-under-cap` / `unparseable-session-keeps-under-cap` ([`skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh`](skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh) `251-278`): four dirs after install, below cap 8; expecting all four kept is consistent with `VERSION_COUNT > KEEP_LIMIT` being false. `PLUGIN_ROOT_VERSION` / `INSTALLED_VERSION` interaction: the script adds `basename "$PLUGIN_ROOT"` to `ACTIVE_SESSION_VERSIONS` even when that version is already listed from sessions; duplicates do not change protection or ordering. No extra prune beyond the two unpinned oldest in the over-cap cases above.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

### FINDING_21: risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:311-350
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Cap-loop refactor is broader than the plan's floor-sweep removal-only narrative. Reviewers may mis-attribute future prune regressions to the wrong change. Document cap-loop semantic change in the PR summary.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

### FINDING_22: risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:328-350
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Cap-phase prune loop adds PRUNE_FAILED_VERSIONS skips without a targeted regression test. Cap-phase rm failure for one oldest unpinned directory is untested; behavior (warnings partial prune vs cap) may drift without CI signal. Add RM_FAIL_VERSION (or equivalent) case targeting a cap-prune removal in test-upgrade-larch.sh or test-upgrade-larch-prune.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_3

### FINDING_3: **correctness** — same file `279-295` in diff / `280-295` current (`cap-prune-trims-to-eight`): nine seeds `29.1.21`–`29.1.29`, install `29.1.30` → ten dirs; only `LATEST_STABLE` and executing `29.1.29` are protected among removals; two removals (`21`, `22`) leave eight (`23`–`30`). Consistent.
- **Reviewer**: dyn-test-case-arithmetic-output.txt
- **Concern**: - **correctness** — same file `279-295` in diff / `280-295` current (`cap-prune-trims-to-eight`): nine seeds `29.1.21`–`29.1.29`, install `29.1.30` → ten dirs; only `LATEST_STABLE` and executing `29.1.29` are protected among removals; two removals (`21`, `22`) leave eight (`23`–`30`). Consistent.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_4

### FINDING_4: **correctness** — same file `280-296` (`crlf-session-root-keeps-version`): same counts and pin on `29.1.21` via literal line; same prune pair and kept set as above.
- **Reviewer**: dyn-test-case-arithmetic-output.txt
- **Concern**: - **correctness** — same file `280-296` (`crlf-session-root-keeps-version`): same counts and pin on `29.1.21` via literal line; same prune pair and kept set as above.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_5

### FINDING_5: **correctness** — same file `297-315` (`multi-pinned-oldest-still-trims-to-eight`): pins `29.1.20` and `29.1.21` plus executing `29.1.21`; ten dirs after install; two removals must be `29.1.22` and `29.1.23`; eight kept including both pins and `30`. Consistent.
- **Reviewer**: dyn-test-case-arithmetic-output.txt
- **Concern**: - **correctness** — same file `297-315` (`multi-pinned-oldest-still-trims-to-eight`): pins `29.1.20` and `29.1.21` plus executing `29.1.21`; ten dirs after install; two removals must be `29.1.22` and `29.1.23`; eight kept including both pins and `30`. Consistent.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

### FINDING_9: `7572fc49` — Fix upgrade-larch cache pruning floor sweep  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `7572fc49` — Fix upgrade-larch cache pruning floor sweep
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

