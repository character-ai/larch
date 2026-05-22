### FINDING_27: risk-integration: skills/fix-issue/scripts/find-lock-issue.sh:230-257;skills/fix-issue/scripts/find-lock-issue.md:11;.claude/skills/audit-runs/scripts/audit-scan-run.sh;.claude/skills/audit-runs/scans.tsv;CHANGELOG.md;Makefile
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Substantial changes outside the seven-item audit-title plan appear in the same branch diff. A plan-fidelity pass against only the supplied audit-title checklist cannot account for main-sync gating, OOS silent-drop scan, and other merged features. Split PRs or extend the plan so every shipped change maps to an enumerated requirement.
- **Suggested revision**: Address the concern above.



