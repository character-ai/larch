### FINDING_13: [OUT_OF_SCOPE] Pre-rebase fixup commits all tracked dirty paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Pre-rebase `git add -u` fixup in `scripts/ship-pr.sh:934-951` / `2853-2868` commits all tracked dirty paths (#3209). Unrelated tracked edits during CI rebase—or tracked files with secrets modified during the run—can be swept into `chore: pre-rebase working-tree fixup` and pushed on the implement PR without redaction. Not Stage 5 scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Narrow staging to known paths or document operator precondition.
  - From cursor-specialist-security-output.txt: Limit fixup to an allowlisted path set, run redact-secrets on staged content, or stall when dirty paths are outside that set.


Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=2 Result=rejected

### FINDING_14: [OUT_OF_SCOPE] Branch diff noise for Stage 5 reviewers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Three of five commits (#3212, #3209, larch-logs) and related harness/docs churn are outside the Stage 5 hardening plan. Increases review/merge surface for work labeled “Piece 5 of 5”; plan fidelity for STA-3120 Piece 5 should be judged on `423c07a3e`, not full `main..HEAD`. Large rebump/cleanup test blocks add CI time/flake risk when bisecting Stage 5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Consider splitting or rebasing so the hardening PR is reviewable in isolation.
  - From cursor-specialist-plan-fidelity-output.txt: None for Piece 5 code; consider splitting unrelated fixes into separate PRs if reviewers need a plan-pure diff.
  - From cursor-specialist-testing-output.txt: Keep rebump work in its own PR or commit range.
  - From cursor-specialist-testing-output.txt: Exclude cleanup hang-fix tests from Stage 5 PR via rebase/split.


Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=2 Result=rejected

### FINDING_15: [OUT_OF_SCOPE] Cleanup retention uses top-level mtime only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: #3212 replaces descendant activity scan with top-level `find … -mtime +N` only. Directories with stale top-level mtime but recent deep files—or active runs that only touch deep paths—may be deleted earlier than before, depending on filesystem parent-mtime behavior. Out of scope for Stage 5; verify #3212 acceptance separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: If that scenario matters in production, either restore a bounded descendant activity probe for directories only, or document that operators must touch the session root periodically; `SECURITY.md` already documents the top-level-mtime tradeoff.
  - From cursor-specialist-edge-cases-output.txt: Document operator discipline or restore descendant activity scan if false deletion is observed in production.


Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=2 Result=rejected

### FINDING_16: [OUT_OF_SCOPE] `review-and-fix.sh` follow-up uses `git add -A`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Follow-up commit uses `git add -A` (`skills/review-and-fix/scripts/review-and-fix.sh:441-502`), which can stage untracked files (e.g. `.env`) left between commits, not only tracked residue from the first commit. From #3209 / dirty-tree work, not Stage 5 hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Prefer `git add -u` (or an explicit path list) for the follow-up commit if only tracked residue should be captured.
  - From cursor-specialist-security-output.txt: Use `git add -u` for follow-up or path allowlist (separate change).


Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=2 Result=rejected

### FINDING_17: [OUT_OF_SCOPE] Cleanup swallows `find` enumeration errors
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `find` enumeration errors are swallowed (`skills/cleanup/scripts/cleanup.sh:43,85` and related). Permission denied or I/O failure can make cleanup exit 0 with zero removals while stale secrets persist—looks like successful no-op cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Consider surfacing find failures on stderr and non-zero exit when enumeration fails.
  - From cursor-specialist-edge-cases-output.txt: Surface find failures on stderr and exit non-zero when enumeration fails (separate from Stage 5).


Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=2 Result=rejected

### FINDING_18: [OUT_OF_SCOPE] SECURITY.md still references breadcrumbs helper
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Operator diagnostic section (`SECURITY.md:211-214`) still references breadcrumbs helper for design-log publish redaction—misleading for auditors reading the publication redaction path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Update wording to name design-log-publish.sh / larch-log.sh pipelines directly in a follow-up doc fix.


Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=2 Result=rejected

### FINDING_19: [OUT_OF_SCOPE] Plan-complete note: `.completed` harness optional
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Ancestor guard for `.completed/` is implemented and documented; plan only required render-cache and plan-review harnesses—no dedicated ancestor-race harness is a plan-complete omission, not a fidelity gap. Optional future harness could mirror other subtrees.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No slot-specific fix beyond plan-fidelity acknowledgment; overlaps informational with **FINDING_6** if a harness is desired later.)

Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=2 Result=rejected

