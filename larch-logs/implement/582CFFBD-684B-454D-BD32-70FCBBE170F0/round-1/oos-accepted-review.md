### FINDING_2: [OUT_OF_SCOPE] Branch scope, plan coverage, and review/rollback coupling
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The branch bundles many unrelated surfaces (preflight/main-sync, scans, Makefile, agent-lint, changelog, version, docs, implement skill, find-lock, larch-logs, etc.) relative to a narrow audit-title plan, so reviewers and release managers cannot regression-scope or cherry-pick from the plan alone; rollback cost is high.
- **Suggested revision**: Split into separate PRs each with one user-visible story, or extend the written plan and PR description so every changed surface is an explicit numbered requirement.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_9: [OUT_OF_SCOPE] Stale Bash claim in committed run-log review JSON
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Committed review JSON repeats an incorrect Bash 3.2 / `declare -A` claim against current `oos-disposition-shared.inc.bash`, which can send operators after a phantom defect if run logs are treated as live truth.
- **Suggested revision**: Treat as historical transcript; regenerate or annotate only if those log files are edited for other reasons.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


