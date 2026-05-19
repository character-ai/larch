### FINDING_1: **Nit** `correctness` — `scripts/ship-pr.sh:575-591`: the new fallback reads `PR_TITLE` in `scripts/implement-finalize.sh:697-704`, and the new harness supplies it in `skills/implement/scripts/test-step-8a-changelog.sh:128-132`, but the production postbump state writer never includes `PR_TITLE`. In a real no-manifest fallback run, the changelog entry will be `Closed: #N` even when the main ship state already has a PR title, so the test covers a richer state than production can provide. Add `PR_TITLE=$(read_state PR_TITLE)` to `write_postbump_state` and pin that path in the ship-pr or finalize harness.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `correctness` — `scripts/ship-pr.sh:575-591`: the new fallback reads `PR_TITLE` in `scripts/implement-finalize.sh:697-704`, and the new harness supplies it in `skills/implement/scripts/test-step-8a-changelog.sh:128-132`, but the production postbump state writer never includes `PR_TITLE`. In a real no-manifest fallback run, the changelog entry will be `Closed: #N` even when the main ship state already has a PR title, so the test covers a richer state than production can provide. Add `PR_TITLE=$(read_state PR_TITLE)` to `write_postbump_state` and pin that path in the ship-pr or finalize harness.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] code-quality: CHANGELOG.md:574
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Pre-existing changelog entry references skipped-no-bullets routing removed from implement-finalize.md enum. Readers may think skipped-no-bullets is still a live CHANGELOG_STATUS token. None required for this PR; update only if you want changelog narrative consistency with current enums.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: CHANGELOG.md:574
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Historic bullet references skipped-no-bullets semantics. Narrative drift from current STATUS tokens. Optional doc cleanup outside this diff.
- **Suggested revision**: Address the concern above.

### FINDING_4: architecture: .claude/skills/bump-version/SKILL.md:93
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] apply-bump.md edit-in-sync requires SKILL.md update for apply-bump behavior changes; new exit 4 not documented in How it works. Users relying on SKILL.md miss the distinct unmerged-path exit used by ship-pr routing. Document exit 4 alongside exit 1 dirty-tree semantics per apply-bump.md.
- **Suggested revision**: Address the concern above.

### FINDING_5: architecture: skills/implement/references/rebase-rebump-subprocedure.md (step 1b rationale (2))
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Step 1b still implies log-flush ordering is required for drop-bump-commit to work. Walk-back makes ordering non-essential for drop success; readers may over-commit to flush ordering or misunderstand failure modes. Clarify that ordering is hygiene / conflict avoidance rather than a hard prerequisite for drop-bump.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/implement-finalize.sh:711
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Execution-issue ERROR= wording diverges from Item J plan’s exact stub string. Downstream copy/paste greps keyed to the plan phrase may miss this failure mode. Match plan wording or explicitly version the diagnostic vocabulary in docs.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: skills/implement/references/rebase-rebump-subprocedure.md:step1-warn
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] DROPPED=false warning text still blames HEAD-not-bump semantics. Operators debugging walk-depth misses or guard-4 failures get a misleading stall narrative. Generalize the warning to enumerate modern DROPPED=false causes or point at drop-bump-commit stderr WARN lines.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:97-107
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Item E prescribed ERROR copy with rebase-in-progress phrasing and tests keyed to rebase substring; branch emits unmerged paths present and tests that string instead. Downstream matchers or operators following the written plan never see the promised substring; plan-to-test traceability for Item E is broken. Match plan ERROR text and test anchors or revise the plan if the new copy is canonical.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/implement-finalize.sh:695-715
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Issue-J fallback triggers for any empty bullet set after collect_changelog_bullets, including non-JSON MANIFEST_PATH (#2233 silent-empty path). With default ISSUE_NUMBER=456 and manifest-non-json.env (test-implement-finalize.sh:1021-1024), postbump can still return STATUS=ok while amending CHANGELOG with a synthetic Closed:#456 bullet, contradicting collect_changelog_bullets' no-bullets-from-non-JSON contract and mis-documenting the release. Gate ISSUE_NUMBER/PR_TITLE fallback to intended cases (empty manifest path or JSON manifest with empty bullets); keep #2233 non-JSON wiring on the old skip/warn semantics without synthetic bullets.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/implement-finalize.sh:708-711
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Item J required ERROR=Cannot generate changelog bullet: no manifest AND no tracking-issue context.; branch uses summary bullets absent wording and tests lock that in. Greps or incident playbooks written from the plan miss real failures. Use the plan literal for ERROR= (or update plan and harness together).
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/implement/scripts/test-step-8a-changelog.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan described a narrow shim around maybe_update_changelog; harness copies full implement-finalize.sh with PATH stubs. Low risk: harder to maintain than a minimal shim though coverage is good. Optional refactor to a slimmer harness if maintainers want literal plan structure.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: .claude/skills/bump-version/scripts/apply-bump.sh:102-107
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Exit-4 error copy and harness differ from implementation plan wording and fixture technique. External checklists or greps keyed to plan text rebase in progress miss the shipped message. Align ERROR copy and test with plan or document shipped phrase as canonical in apply-bump.md.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/drop-bump-commit.sh:773-785
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New rebase --onto failure path has no regression test for exit 1 or abort cleanup. A bad replay conflict could regress without CI signal. Add a harness that forces rebase onto failure and asserts exit 1 and clean rebase state.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/implement-finalize.sh:707-712
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Execution-issues ERROR= wording differs from Item J plan token. Downstream greps for plan-stable ERROR substring miss the new line. Match plan wording or update plan docs to the shipped sentence.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/test-drop-bump-commit.sh:1229
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Test 18 discards stderr so WARN-only regressions hide. Harness passes while stderr diagnostics break. Capture stderr or assert absence of WARN patterns explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/implement/references/rebase-rebump-subprocedure.md (step 1 DROPPED=false guidance)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] DROPPED=false warning text still describes HEAD-not-bump-only failure modes. After walk-back drop-bump false positives include max-depth exhaustion and failed guards on a deeper bump; operators may apply wrong recovery (e.g. assume CI fix on top) from stale prose. Reword the execution-issues template to cover walk-back depth exhaustion and non-HEAD guard failures.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/implement/references/rebase-rebump-subprocedure.md:32
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] DROPPED=false warning text still assumes bump must be at HEAD and lists only legacy causes. After Item H drop-bump can return DROPPED=false for max-depth miss bad flags empty LARCH_BUMP_FILES parse etc operators read execution-issues text and debug the wrong root cause. Reword warning to point at drop-bump-commit stderr WARN or list new DROPPED=false families.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/implement/references/rebase-rebump-subprocedure.md:32-38
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] After Item H walk-back, DROPPED=false causes expanded beyond HEAD-not-bump; warning template still says HEAD was not a bump commit; step 1b rationale (2) still claims flush must sit below bump for drop correctness. Operators mis-attribute DROPPED=false after max-depth or Guard 4 failures; rationale (2) mis-explains why flush-before-rebase still matters versus drop-bump mechanics. Rewrite warning causes and bullet (2) to match walk-back semantics.
- **Suggested revision**: Address the concern above.

### FINDING_19: security: scripts/create-pr.sh (gh pr create failure diagnostics)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Unescaped stderr/stdout tail from gh is embedded in one diagnostic line. Hostile or corrupted gh output could confuse markdown/terminal consumers of execution-issues or logs. Bound length strip control chars or use delimited multi-line diagnostics.
- **Suggested revision**: Address the concern above.

### FINDING_20: security: scripts/implement-finalize.sh (maybe_update_changelog fallback PR_TITLE)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] PR_TITLE from state is interpolated into CHANGELOG without sanitization. A crafted issue title could distort changelog markdown or readability. Normalize title (newlines quotes length) before writing the fallback bullet.
- **Suggested revision**: Address the concern above.

