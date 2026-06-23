# Review Round 1

- Mode: `diff`
- 3 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Part 1 incomplete — three listed modules lack local-var annotations
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Part 1 lists 17 design-lifecycle modules but the typing commit annotates only 15. `python/decompose.py`, `python/plan_scout.py`, and `python/design_summary.py` were not touched; non-obvious locals (e.g. `data = json.loads(...)` in `plan_scout.py:248`, `row = json.loads(...)` in `decompose.py:481` and `decompose.py:572`) remain unannotated. Acceptance requiring non-obvious locals annotated across the full listed set cannot be verified; pyright coverage for those modules is unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add surgical local annotations to the missing modules or explicitly defer them in the plan with a follow-up issue.
  - From codex-specialist-correctness-output.txt: Audit `python/decompose.py` and `python/plan_scout.py`, annotate the remaining non-obvious locals, or document why each listed file needed no changes.
  - From cursor-specialist-testing-output.txt: Annotate non-obvious locals in the three missing files or document an explicit deferral with a tracked follow-up chunk.


### FINDING_2: `complexity-baseline.json` edited outside 17-file allowlist
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The typing commit modifies `python/complexity-baseline.json` outside the Part 1 file list, including rows for symbols in unrelated modules (e.g. `ci_monitor` `poll_ci`, `run_logs` `_commit_run`) without matching source edits in that commit. This violates plan acceptance ("No source changes outside the listed files"), mixes CI baseline churn into a typing PR, and risks baseline/source desync on cherry-pick or bisect (false CI passes or unexpected `make py-lint` complexity-baseline failures).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove complexity-baseline.json from the Part 1 commit; keep baseline updates with the owning CI/refactor commit.
  - From cursor-specialist-edge-cases-output.txt: Co-locate baseline updates with the commits that change the referenced symbols.
  - From cursor-specialist-testing-output.txt: Remove unrelated baseline edits from the typing commit; regen baseline only in commits that change the corresponding source complexity.


### FINDING_4: Branch changes code outside approved 17-file design-lifecycle list
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Despite plan constraints ("Touch only the files listed above", "No source changes outside the listed files"), the branch changes code outside the allowed design-lifecycle file list. Affected paths include `python/ci_monitor.py`, `python/config.py`, `python/exec_issue_detail.py`, `python/final_report.py`, `python/lint_consecutive_bash.py`, `python/oos_filer.py`, `python/voting.py`, multiple `python/test_*.py` files, and `skills/design/references/brainstorm.md`. Part 1 cannot ship or revert as a type-only design-lifecycle audit because CI monitoring, final report rendering, linting, OOS filing, and voting behavior would ship with it; reviewers and CI cannot verify typing-only regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Rebase onto a main that already contains #5072/#5090, or split those unrelated changes out. Leave only the approved 17 files for this part.
  - From cursor-specialist-edge-cases-output.txt: Split PRs or reset branch to typing-only file scope.
  - From cursor-specialist-testing-output.txt: Split or rebase so Part 1 PR contains only design-lifecycle typing changes.
  - From codex-specialist-testing-output.txt: Split or drop unrelated changes, or revise the scope and acceptance criteria before shipping.


