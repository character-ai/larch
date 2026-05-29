### FINDING_11: [OUT_OF_SCOPE] SECURITY.md still describes monitor sidecar as publish inputs
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Doc still mentions monitor sidecar filenames as silently skipped publish inputs. Operators may think live monitor files are still produced at runtime. Clarify legacy-only wording in Stage 5 or a small doc-only follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_3: [OUT_OF_SCOPE] run-step5-review.md still documents monitor pairing until Stage 4
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Sibling doc still claims skill fences carry the monitor pair until Stage 4. After merge an operator reads run-step5-review.md and expects breadcrumb-monitor pairing that SKILL.md no longer documents. Update the contract to foreground-only Step 5 invocation; remove the until Stage 4 sentence. File was not modified on this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] collect-agent-results.md still uses Family B writer wording
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Script sibling docs still call collectors Family B writers. Terminology drift makes Stage 4 completion harder to grep-verify for authors. Replace with neutral blocking-writer wording or a one-line Stage 4 past-tense note.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] .gitleaks.toml allowlist references deleted breadcrumb-monitor tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Allowlist still names deleted test-breadcrumb-monitor files. None functional; adds noise when auditing gitleaks config. Remove the two stale path patterns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] No CI/make gate for plan final forbidden-token grep
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No automated CI target enforces the plan final grep gate after lint-foreground-markers removal. PR merges with forbidden Family-B strings in un-pinned files if implement close grep is skipped; structure tests only catch regressions where pins exist. Wire a small make target or pre-commit check for the forbidden token set (excluding larch-logs and forensics paths), or expand structure pins per finding #1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

