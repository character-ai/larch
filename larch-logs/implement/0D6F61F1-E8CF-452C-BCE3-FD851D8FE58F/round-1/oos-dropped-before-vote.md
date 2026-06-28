### OOS_1: [OUT_OF_SCOPE] Architectural-guidelines exit routing and present+ok lazy-load path verified in SKILL.md
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: nit
- **Concern**: `present` + `DIFF_STATUS=failed` routes only through prepare exit-code handling (`prepare_main` returns `1`; test at `python/test_architectural_guidelines.py:754`). `present` + `DIFF_STATUS=ok` is the only path that loads the new present reference. Exit routing for hard prepare failure, absent, invalid, and present+diff-failed remains inline in `skills/implement/SKILL.md`. Targeted harnesses report PASS for architectural-guidelines step, implement structure, plan-adequacy audit, and fence-shape checks.

### OOS_2: [OUT_OF_SCOPE] Rare implement prompt paths relocated to lazy-loaded references per plan
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: nit
- **Concern**: `BYPASS kind=` grammar is absent from `SKILL.md` and present in `force-mode.md`. Write-staged fence is absent from `SKILL.md` and present in `architectural-guidelines-present.md`. Rare `--force` bypass grammar moved to `skills/implement/references/force-mode.md`; `SKILL.md` keeps the flag row, item-4 skip breadcrumb, and no-audit/no-bypass-log contract. Present+ok assessment moved to `architectural-guidelines-present.md`; `SKILL.md` keeps prepare fence, exit-code routing, and terse status branches. `conflict-resolution.md` requires full Phase A subsection re-entry. Harnesses updated (`EXPECTED_NEW` 22→21; force grammar pins relocated; present-path and conflict-rerun pins added). New references include Consumer / Contract / When to load triplet (`test-references-headers.sh` covers them repo-wide). `agent-lint.toml` excludes `step-architectural-guidelines-write-staged.{sh,md}` after the write-staged fence left always-loaded `SKILL.md`.

