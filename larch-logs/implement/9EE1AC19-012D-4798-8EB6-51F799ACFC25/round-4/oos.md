### FINDING_22: [OUT_OF_SCOPE] `commit_changelog` Markdown-only vs Phase 7 RST
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `commit_changelog` Markdown-only matches bash, not Phase 7 RST commit needs. Out of scope unless RST CHANGELOG commits required before Phase 7. Defer or extend when RST commit path is required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Defer or extend when RST commit path is required


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_23: [OUT_OF_SCOPE] Phase 2 config constants not in `documented_constants_exist`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Phase 2 config constants not in `documented_constants_exist` test. Pre-existing test pattern not amplified by this branch. Optionally extend `test_config` when touching config again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optionally extend test_config when touching config again


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_32: [OUT_OF_SCOPE] Bash classify also defaults failed diff to PATCH
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Bash and Python both treat failed `git diff --name-status` as empty diff defaulting to PATCH. Git errors silently produce PATCH instead of failing loud; pre-existing bash behavior not introduced by this branch. Fix in a future phase if fail-loud classification is desired; not a regression from this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Fix in a future phase if fail-loud classification is desired; not a regression from this diff.


Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=1 Result=neutral

### FINDING_36: [OUT_OF_SCOPE] No RST parity test for `auto_resolve` with subsection under Unreleased
- **Reviewer(s)**: dyn-rst-section-parser-output.txt
- **Severity**: nit
- **Concern**: `_auto_resolve_rst` uses `_rst_second_title_index`, so RST changelogs with a subsection directly under `Unreleased` (as in `RST_SAMPLE` lines 62–65) merge only the lines before that subsection; this mirrors `scripts/auto-resolve-changelog.sh:249-266`, but there is no parity test with that subsection shape—only flat `Unreleased` → bullets → `Version` fixtures (`python/test_changelog.py:269-314`).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_37: [OUT_OF_SCOPE] RST lacks Markdown-style Semantic Versioning intro anchor
- **Reviewer(s)**: dyn-rst-section-parser-output.txt
- **Severity**: nit
- **Concern**: RST has no Markdown-style “Semantic Versioning” intro anchor fallback in `_write_rst_entry` (only `_rst_merge_first_index`); that is a broader Phase 2 policy gap, not introduced by the section-end helper alone.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] No repo-wide pytest conftest for Runner doubles
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: No shared pytest conftest/helpers for Runner doubles repo-wide. Other phases may repeat the same duplication pattern. Add conftest/helpers when multiple modules need identical Runner fakes (pre-existing gap).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

