### FINDING_1: **correctness** — [`skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh`](skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh) `233-249` (`active-session-keeps-version`): nine seeded dirs `29.1.20`–`29.1.28`, install `29.1.30` → ten dirs; `LATEST_STABLE` `29.1.30`; pins/executing protect `29.1.21`; removable oldest are `29.1.20` then `29.1.22`; eight kept (`21`, `23`–`28`, `30`). Arithmetic matches assertions.
- **Reviewer**: dyn-test-case-arithmetic-output.txt
- **Concern**: - **correctness** — [`skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh`](skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh) `233-249` (`active-session-keeps-version`): nine seeded dirs `29.1.20`–`29.1.28`, install `29.1.30` → ten dirs; `LATEST_STABLE` `29.1.30`; pins/executing protect `29.1.21`; removable oldest are `29.1.20` then `29.1.22`; eight kept (`21`, `23`–`28`, `30`). Arithmetic matches assertions.
- **Suggested revision**: Address the concern above.

### FINDING_2: **correctness** — `no-sessions-keeps-under-cap` / `unparseable-session-keeps-under-cap` ([`skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh`](skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh) `251-278`): four dirs after install, below cap 8; expecting all four kept is consistent with `VERSION_COUNT > KEEP_LIMIT` being false.
- **Reviewer**: dyn-test-case-arithmetic-output.txt
- **Concern**: - **correctness** — `no-sessions-keeps-under-cap` / `unparseable-session-keeps-under-cap` ([`skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh`](skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh) `251-278`): four dirs after install, below cap 8; expecting all four kept is consistent with `VERSION_COUNT > KEEP_LIMIT` being false. `PLUGIN_ROOT_VERSION` / `INSTALLED_VERSION` interaction: the script adds `basename "$PLUGIN_ROOT"` to `ACTIVE_SESSION_VERSIONS` even when that version is already listed from sessions; duplicates do not change protection or ordering. No extra prune beyond the two unpinned oldest in the over-cap cases above.
- **Suggested revision**: Address the concern above.

### FINDING_3: **correctness** — same file `279-295` in diff / `280-295` current (`cap-prune-trims-to-eight`): nine seeds `29.1.21`–`29.1.29`, install `29.1.30` → ten dirs; only `LATEST_STABLE` and executing `29.1.29` are protected among removals; two removals (`21`, `22`) leave eight (`23`–`30`). Consistent.
- **Reviewer**: dyn-test-case-arithmetic-output.txt
- **Concern**: - **correctness** — same file `279-295` in diff / `280-295` current (`cap-prune-trims-to-eight`): nine seeds `29.1.21`–`29.1.29`, install `29.1.30` → ten dirs; only `LATEST_STABLE` and executing `29.1.29` are protected among removals; two removals (`21`, `22`) leave eight (`23`–`30`). Consistent.
- **Suggested revision**: Address the concern above.

### FINDING_4: **correctness** — same file `280-296` (`crlf-session-root-keeps-version`): same counts and pin on `29.1.21` via literal line; same prune pair and kept set as above.
- **Reviewer**: dyn-test-case-arithmetic-output.txt
- **Concern**: - **correctness** — same file `280-296` (`crlf-session-root-keeps-version`): same counts and pin on `29.1.21` via literal line; same prune pair and kept set as above.
- **Suggested revision**: Address the concern above.

### FINDING_5: **correctness** — same file `297-315` (`multi-pinned-oldest-still-trims-to-eight`): pins `29.1.20` and `29.1.21` plus executing `29.1.21`; ten dirs after install; two removals must be `29.1.22` and `29.1.23`; eight kept including both pins and `30`. Consistent.
- **Reviewer**: dyn-test-case-arithmetic-output.txt
- **Concern**: - **correctness** — same file `297-315` (`multi-pinned-oldest-still-trims-to-eight`): pins `29.1.20` and `29.1.21` plus executing `29.1.21`; ten dirs after install; two removals must be `29.1.22` and `29.1.23`; eight kept including both pins and `30`. Consistent.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] **architecture** — [`larch-logs/implement/DF68EB95-09BD-4B74-BBD1-A23B7B218CD9/`](larch-logs/implement/DF68EB95-09BD-4B74-BBD1-A23B7B218CD9/) (new `manifest.json`, `parent-issue.md`, etc. in the diff): implement run artifacts under `larch-logs/` are unrelated to prune arithmetic; whether they belong on the branch is a process/repo-hygiene choice, not introduced by the test expectations themselves.
- **Reviewer**: dyn-test-case-arithmetic-output.txt
- **Concern**: - **architecture** — [`larch-logs/implement/DF68EB95-09BD-4B74-BBD1-A23B7B218CD9/`](larch-logs/implement/DF68EB95-09BD-4B74-BBD1-A23B7B218CD9/) (new `manifest.json`, `parent-issue.md`, etc. in the diff): implement run artifacts under `larch-logs/` are unrelated to prune arithmetic; whether they belong on the branch is a process/repo-hygiene choice, not introduced by the test expectations themselves. Because there are **no** in-scope correctness issues tied to test-case arithmetic, the in-scope section is “none found” rather than a defect list. I am **not** emitting `NO_ISSUES_FOUND` (that token is defined only when both sections are empty, and the `larch-logs` note is listed out-of-scope).
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] architecture: Makefile:742-752
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Duplicate identical test-upgrade-larch Makefile targets. make uses the last duplicate; minor maintenance noise. Not introduced by this branch diff; dedupe in a separate change if desired.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] architecture: larch-logs/implement/DF68EB95-09BD-4B74-BBD1-A23B7B218CD9/*
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] New implement run log files appear in diff; not required by feature plan. Noise for narrow plan reviews; excluded by reviewer rules for implement logs. No action per repo policy unless you choose to exclude logs from the PR diff review window.
- **Suggested revision**: Address the concern above.

### FINDING_9: `7572fc49` — Fix upgrade-larch cache pruning floor sweep  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `7572fc49` — Fix upgrade-larch cache pruning floor sweep
- **Suggested revision**: Address the concern above.

### FINDING_10: `b282bfeb` — chore(larch-logs): flush implement run DF68EB95-09BD-4B74-BBD1-A23B7B218CD9  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `b282bfeb` — chore(larch-logs): flush implement run DF68EB95-09BD-4B74-BBD1-A23B7B218CD9
- **Suggested revision**: Address the concern above.

### FINDING_11: `d4d4370f` — Address code review feedback (round 1)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `d4d4370f` — Address code review feedback (round 1) Reviewed the precomputed diff at `<TMPDIR>/round-2/diff.txt` (plus a quick read of the current [`upgrade-larch.sh`](skills/upgrade-larch/scripts/upgrade-larch.sh) prune helpers for how `version` is sourced).
- **Suggested revision**: Address the concern above.

### FINDING_12: architecture: implementation_plan §3 test-upgrade-larch-prune.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Unplanned harness case multi-pinned-oldest-still-trims-to-eight (and doc bullet) not listed in plan file checklist. Plan-to-implementation traceability breaks; reviewers cannot tell if the scenario is required acceptance work or scope creep. Extend implementation plan or issue #2380 acceptance criteria to include this case or remove it from the branch.
- **Suggested revision**: Address the concern above.

### FINDING_13: architecture: skills/upgrade-larch/scripts/upgrade-larch.md:18
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] §8 gains new “pins do not consume prune budget” contract language not listed in plan doc edits. Doc/plan checklist misaligned for reviewers tracing only the written plan. Add matching bullet to the plan or trim doc to plan-specified edits only.
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh (multi-pinned-oldest-still-trims-to-eight); skills/upgrade-larch/scripts/test-upgrade-larch-prune.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Extra harness + doc coverage beyond the plan's single new cap-prune case name Minor plan/traceability drift for issue-driven workflows Align plan or issue text with the added multi-pin regression
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: skills/upgrade-larch/scripts/upgrade-larch.md:18
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] 'Each session-derived pin emits…' understates executing-root preservation in the same bullet Readers may think only session-env pins are warned or preserved for cap pruning Clarify session-env vs executing-root pins and when stderr warnings fire
- **Suggested revision**: Address the concern above.

### FINDING_16: code-quality: skills/upgrade-larch/scripts/upgrade-larch.md:18
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Ambiguous 'prune budget' wording may be read as pinned dirs not counting toward the 8-version cap Misinterpretation could surprise operators who assume pins free extra cache slots Reword to: pinned versions are never deleted; pruner removes oldest unpinned dirs until count ≤8 or stuck
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh:295 vs skills/upgrade-larch/scripts/upgrade-larch.sh:323-324
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Two different preservation warning strings for related prune skips Inconsistent operator-facing diagnostics Unify messages via helper with reason, or document intentional difference
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: implementation_plan §3 active-session-keeps-version
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan text implies a single cap removal (29.1.20) for nine seeds + install 29.1.30. Arithmetic needs two removals under KEEP_LIMIT=8; literal plan text understates expected prunes (implementation matches correct count). Update plan wording to mention pruning the two oldest unpinned versions.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: skills/upgrade-larch/scripts/upgrade-larch.md:40-42 (step 8 long line; line numbers approximate in long wrapped paragraph)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Ambiguous wording: pins do not consume prune budget. Reader may believe pinned versions are excluded from the eight-directory retention count and expect more than eight directories to remain when many pins exist; the implementation still enforces total cached versions at or below the cap by pruning unpinned oldest entries. Rewrite to say pins are skipped for deletion but still count toward the cap; the loop deletes oldest unpinned versions until total ≤ KEEP_LIMIT or stuck.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/upgrade-larch/scripts/upgrade-larch.sh:313-350 (approx.; cap-prune while loop per diff)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Cap-prune loop rewritten (while + oldest unpinned + PRUNE_FAILED_VERSIONS) though plan only mandated removing the floor sweep. Plan readers assume only the floor block changed; actual cap semantics and edge handling (e.g. rm failures) changed without a plan anchor. Amend plan/issue to document cap-loop semantics change as part of the fix.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:311-350
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Cap-loop refactor is broader than the plan's floor-sweep removal-only narrative. Reviewers may mis-attribute future prune regressions to the wrong change. Document cap-loop semantic change in the PR summary.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:328-350
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Cap-phase prune loop adds PRUNE_FAILED_VERSIONS skips without a targeted regression test. Cap-phase rm failure for one oldest unpinned directory is untested; behavior (warnings partial prune vs cap) may drift without CI signal. Add RM_FAIL_VERSION (or equivalent) case targeting a cap-prune removal in test-upgrade-larch.sh or test-upgrade-larch-prune.sh.
- **Suggested revision**: Address the concern above.

