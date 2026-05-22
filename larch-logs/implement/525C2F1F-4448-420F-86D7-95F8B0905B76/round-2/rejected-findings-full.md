### [rejected] FINDING_17

### FINDING_17: security: .claude/skills/audit-runs/scripts/audit-scan-run.sh:486-493
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] New scan_oos_silent_drop uses find + awk on discovered paths without excluding symlinks. A tarball or log tree with an oos-accepted*.md symlink pointing outside RUN_DIR makes awk read out-of-tree content and distorts scan results. Use find -type f (and/or reject symlinks) before awk.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0

