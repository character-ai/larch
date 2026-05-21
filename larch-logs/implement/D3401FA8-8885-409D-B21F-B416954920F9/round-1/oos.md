### FINDING_27: [OUT_OF_SCOPE] `audit-close-priors.md` contract vs broader automated-testing narrative
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Doc claims no unit tests while other materials push harness expansion—documentation-only mismatch.
- **Suggested revision**: Reconcile contract text with intended offline stub strategy (or explicit manual-only waiver).


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_28: [OUT_OF_SCOPE] `SKILL.md` vs `audit-title.md` / `audit-title.sh` disagree on non-contiguous title rules
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Concern**: Orchestrator-facing SKILL prose diverges from script contract (≤4 vs explicit list for all gaps).
- **Suggested revision**: Align SKILL + companion `.md` + script behavior under one documented rule.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_29: [OUT_OF_SCOPE] Bash 3.2 portability spot-check (audit-runs scripts)
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Concern**: Reviewer reports no disallowed Bash 4+ features in `.claude/skills/audit-runs/scripts/*.sh` per `BASH_AUTHORING.md` guidance (informational).
- **Suggested revision**: Keep future edits within the same portability constraints.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_30: [OUT_OF_SCOPE] Branch/commit context note (read-only)
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Concern**: Review anchored to branch commit `620377c2` / PR #2495 extraction work (metadata only).
- **Suggested revision**: None (tracking/context for readers).


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_38: [OUT_OF_SCOPE] Spot checks: `emit_error`/`emit_ok` printf format strings; parent-issue grep format; empty-string category semantics; `parse_prior` duplicate-key ambiguity
- **Reviewer(s)**: dyn-kv-contract-output.txt, dyn-jq-shell-logic-output.txt
- **Concern**: Reviewers flag these as likely acceptable / low likelihood / intentional behavior as written (informational cross-checks, not actionable defects).
- **Suggested revision**: None unless product intent changes; optionally document edge-case interpretations explicitly.
```

Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

