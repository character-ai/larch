### FINDING_1: **Important** `correctness` `scripts/ship-pr.sh:1213` / `scripts/ship-pr.sh:1239` — When the regression correction triggers, `new_version` is updated but `reasoning_file` still contains the original `classify-bump.sh` result. Concrete scenario: `classify-bump.sh` emits `NEW_VERSION=29.1.39`, the guard corrects to `29.3.1`, `apply-bump.sh` commits `29.3.1`, then the `version-bump-reasoning` larch-log batch is refreshed from a file that still says the new version is `29.1.39`. Update or append to `BUMP_REASONING_FILE` when correction happens so the recorded audit trail includes the corrected version and why it changed.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/ship-pr.sh:1213` / `scripts/ship-pr.sh:1239` — When the regression correction triggers, `new_version` is updated but `reasoning_file` still contains the original `classify-bump.sh` result. Concrete scenario: `classify-bump.sh` emits `NEW_VERSION=29.1.39`, the guard corrects to `29.3.1`, `apply-bump.sh` commits `29.3.1`, then the `version-bump-reasoning` larch-log batch is refreshed from a file that still says the new version is `29.1.39`. Update or append to `BUMP_REASONING_FILE` when correction happens so the recorded audit trail includes the corrected version and why it changed.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Nit** `risk-integration` `.claude/skills/bump-version/SKILL.md:53` — `apply-bump.sh` now has a new fail-closed regression error, but the shipped `/bump-version` skill prompt still documents only the same-version origin failure path. Add the regression guard/error behavior there too; `apply-bump.md` explicitly lists this SKILL file as an edit-in-sync target for behavior changes.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `risk-integration` `.claude/skills/bump-version/SKILL.md:53` — `apply-bump.sh` now has a new fail-closed regression error, but the shipped `/bump-version` skill prompt still documents only the same-version origin failure path. Add the regression guard/error behavior there too; `apply-bump.md` explicitly lists this SKILL file as an edit-in-sync target for behavior changes.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: docs/linting.md (not in diff)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] make test-apply-bump description omits regression case. Docs lag harness unless updated elsewhere. Update linting.md when editing docs next.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] correctness: .claude/skills/bump-version/scripts/classify-bump.sh:219-225
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Leading-zero version segments and bash arithmetic. Unusual version strings could confuse MAJ/MIN/PAT arithmetic; pre-existing. No change required for this PR scope.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: docs/linting.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] make test-apply-bump narrative omits new regression case File not modified; central doc drifts from scripts/test-apply-bump.md case 8 Update linting doc row when convenient
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: scripts/ship-pr.sh:380-392,.claude/skills/bump-version/scripts/apply-bump.sh:41-51
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] semver_lt duplicated in two scripts. Future semantic changes could diverge between paths. Shared helper or cross-reference comment.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: .claude/skills/bump-version/scripts/apply-bump.md:25
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Top failure list omits regression guard while invariants mention it. Readers see inconsistent contract summary at file top. Add regression case to the exit-1 sentence.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: .claude/skills/bump-version/scripts/apply-bump.md:60-65 (+ sibling SKILL.md)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] apply-bump.md Edit-in-sync requires SKILL.md updates for apply-bump behavior changes; SKILL.md still omits regression guard. Operators following SKILL see incomplete apply-bump contract vs scripts and md invariants. Update .claude/skills/bump-version/SKILL.md apply-bump bullets for regression probe and failure text.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: .claude/skills/bump-version/scripts/apply-bump.md:7,25
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Purpose and exit-code paragraphs omit regression guard while Invariants describe it. Readers of the primary contract miss the new failure mode until they scroll to Invariants. Update Purpose line and exit-1 sentence to include regression guard.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: .claude/skills/bump-version/scripts/apply-bump.sh:1-22
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Header contract omits regression guard among pre-commit failure modes. Readers miss that exit 1 includes regression without reading apply-bump.md Invariants. Extend header/exit-code comment to mention NEW_VERSION < ORIGIN_VERSION.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: .claude/skills/bump-version/scripts/apply-bump.sh:9-11,22
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Header comments omit regression guard. Misleading skim-level contract for contributors. Update file header and exit-code comment.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: .claude/skills/bump-version/scripts/apply-bump.sh:9-12,.claude/skills/bump-version/scripts/apply-bump.sh:22
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Header comments omit regression pre-commit check. Maintainers skim headers and miss new behavior. Update script header to list regression guard and exit-1 case.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: scripts/ship-pr.sh:385-396; .claude/skills/bump-version/scripts/apply-bump.sh:41-51
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate semver_lt helper. Future semver tweak must be edited twice; easy to diverge. Extract to shared sourced helper.
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: scripts/test-apply-bump.sh:103-106,312-315
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Sub-test H uses default 2.0.0 not plan-specified 2.9.9. Weaker alignment with planned scenario naming; still valid functionally. Use 2.9.9 for case H via dedicated invoke path.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: .claude/skills/bump-version/SKILL.md:53-59,.claude/skills/bump-version/SKILL.md:92
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] How it works / exit codes omit NEW_VERSION < ORIGIN_VERSION regression guard and new ERROR pattern. Agent follows SKILL and mis-handles or does not expect apply-bump version regression failures. Update SKILL.md bullets to mirror apply-bump.md (equality + ordering probes and regression ERROR).
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:41-50,scripts/ship-pr.sh:230-239
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] semver_lt uses bash integer -lt on dot fields; leading-zero components allowed by regex. Rare pathological versions could mis-order vs intended semver. Normalize numeric fields or use semver-aware compare.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/ship-pr.sh:1199-1216,scripts/ship-pr.sh:1237-1247
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] After correcting new_version, version-bump-reasoning still uploads unchanged classify reasoning_file. Audit log shows pre-correction New version while branch lands corrected semver. Append correction to reasoning, regenerate stub, or document WARN line as override.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/ship-pr.sh:1199-1247
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] After version-regression correction, larch-log still refreshes from classify-bump reasoning_file written for pre-correction NEW_VERSION. PR title and committed bump can show 29.3.1 while version-bump-reasoning batch still documents 29.1.39 and prior rationale, breaking audit consistency in the exact mis-merge scenario this feature targets. On correction path, amend or regenerate reasoning before larch-log write, or skip overwrite when new_version was corrected.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: scripts/ship-pr.sh:1207-1211
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unknown bump_type falls through case *) to _corrected=new_version leaving regression unfixed at the ship-pr correction layer. Unexpected BUMP_TYPE token with semver_lt true skips auto-correction until apply-bump fails closed. Treat unknown bump_type as fatal for this path or normalize before case.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: .claude/skills/bump-version/scripts/apply-bump.md:25
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] exit-code summary omits version-regression failure despite new behavior Readers relying on the opening contract miss the new fail-closed path Extend the exit-1 list to mention NEW_VERSION < ORIGIN_VERSION regression
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: .claude/skills/bump-version/scripts/apply-bump.md:25-26
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Output Contract paragraph omits regression from the exit-1 list despite new behavior. Doc readers scanning Purpose/Output miss the new failure class. Add version regression to the enumerated exit-1 causes.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: .claude/skills/bump-version/scripts/apply-bump.md:58-62
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Edit-in-sync lists skills/implement/SKILL.md not updated in this PR. Repo convention says sync Step 8 bump failure guidance when apply-bump.sh changes. Add Step 8 note for version regression ERROR or narrow the rule text if intentional.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: .claude/skills/bump-version/scripts/apply-bump.md:60-63,skills/implement/SKILL.md
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Edit-in-sync requires skills/implement/SKILL.md update; branch did not change it. Process/checklist gap for Step 8 docs if operators need the new ERROR pattern. Add minimal Step 8 note if failure semantics matter for orchestrators.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: .claude/skills/bump-version/scripts/apply-bump.sh:111-112
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] fetch-failure error string only references same-version race fetch also gates regression check; message is slightly misleading Reword to cover both origin/main guards
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/ship-pr.sh:1199-1217
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] run_rebase_rebump version-regression correction is not exercised by any automated test apply-bump regression is covered; wrong MAJOR/MINOR/PATCH correction or WARN/state handling could ship without CI signal Add stubbed ship-pr harness coverage or unit-test extracted correction helper
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: scripts/ship-pr.sh:1199-1247
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] After correcting regressed new_version the reasoning_file passed to larch-log still documents classify's uncorrected NEW_VERSION. Mis-resolved conflict produces classify NEW_VERSION 29.1.39 while origin/main is 29.3.0; ship-pr corrects to 29.3.1 for apply-bump but version-bump-reasoning batch still shows 29.1.39 in markdown. Append a correction note to reasoning_file or rewrite the New version line before larch-log.sh write.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: scripts/ship-pr.sh:689-724
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] run_bump_phase only maps same-version ERROR to exit 5; version regression errors stall at 8 and lack run_bump_phase-side correction. If initial bump path ever hits NEW_VERSION < ORIGIN_VERSION without run_rebase_rebump correction, user gets stall 8 instead of same-version-style exit 5 recovery. Mirror correction in run_bump_phase or extend ERROR case routing per intended UX.
- **Suggested revision**: Address the concern above.

