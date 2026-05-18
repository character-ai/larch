### [rejected] FINDING_10

### FINDING_10: code-quality: scripts/git-push.sh:2757-2776; scripts/rebase-push.sh:246-276; scripts/ship-pr.sh:1149-1177
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Jitter/backoff formula duplicated across three scripts with integer truncation. Future edits can drift one copy and diverge backoff semantics. Extract a one-function helper or centralize the comment+formula once.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_11

### FINDING_11: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:96-107
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Internal-artifact filter is line-regex plus awk $2 WARN list. Unusual git status quoting or paths with spaces can bypass tolerance or mis-report WARN targets. Use NUL-safe status parsing or a path-based allowlist without awk field splitting.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_12

### FINDING_12: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:96-107
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Porcelain line filtering and awk column 2 for WARN may mishandle quoted or multi-token paths from git status. Internal artifacts with unusual path metadata might still fail the bump (safe) or emit an incomplete WARN path (cosmetic). Optional: parse porcelain with -z or match paths after the status prefix without assuming a single-token path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_7

### FINDING_7: architecture: scripts/compose-review-findings.sh:57-72 scripts/compose-review-findings.md scripts/test-compose-review-findings.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] HTML-escape pipeline for composed findings is bundled with ship-pr resilience work. Revert/cherry-pick/bisect conflates two unrelated behavioral changes; review surface and blast radius grow without a single coherent feature story. Split compose escaping into its own PR or commit series.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_9

### FINDING_9: code-quality: scripts/compose-review-findings.sh; scripts/compose-review-findings.md; scripts/test-compose-review-findings.sh; agent-lint.toml; docs/linting.md; Makefile
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Unrelated compose-review-findings HTML-escape + lint/doc/Makefile wiring ships in the same branch as ship-pr/apply-bump resilience. Reviewers must reason about two independent behaviors in one PR; bisect/revert and release notes blur. Split PR or separate commits: resilience vs finding-body escaping.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

