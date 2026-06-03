### FINDING_12: [OUT_OF_SCOPE] configuration-and-permissions.md rebump reference (outside Phase 1 diff)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Same stale rebump reference as in-scope doc finding; file treated as outside the Phase 1 diff. Operator misconfiguration risk remains. Fix in a follow-up docs-only pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_16: [OUT_OF_SCOPE] PR bundles unrelated #3395 Codex quota changes with #3364
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: PR includes unrelated #3395 Codex quota launcher changes alongside #3364. Harder to bisect regressions and higher review noise for a subtractive versioning change. Split or clearly section the PR for reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_17: [OUT_OF_SCOPE] quota regex false-positive risk in external launcher events
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The recall-biased `quota` regex in `scripts/lib-external-launcher-common.sh:275-288` predates this branch; #3395 extends the same classifier to `${OUTPUT}.events.jsonl`. Unrelated echoed text containing `quota` could false-positive as a health/quota failure (vendor routing only). Trade-off is documented and low harm; not introduced as a new vulnerability class here.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_18: [OUT_OF_SCOPE] FORKED_TARGET allows shipping on main/master (pre-existing)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `FORKED_TARGET=true` allows shipping on `main`/`master` when branch names align; pre-existing operator trust signal, unchanged by Phase 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] conflict-resolution.md pre-pass terminology drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: "Non-bump" / "deterministic pre-pass" wording predates Phase 1; pre-pass semantics changed but the file was only lightly touched. Pre-existing terminology drift; not a functional regression from this diff. Clarify pre-pass scope in a docs-only pass when `conflict-resolution.md` is next edited.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] hook-stop-fail-close.sh header mentions post-bump-version protection
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Shell header comment still mentions post-bump-version protection. Cosmetic only; hook behavior matches Phase 1. Update header to match `hook-stop-fail-close.md` on next hook touch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

