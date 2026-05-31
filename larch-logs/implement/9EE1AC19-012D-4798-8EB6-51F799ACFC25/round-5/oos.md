### FINDING_8: [OUT_OF_SCOPE] Overlapping `status()` / `status_porcelain()` in `git.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Overlapping `status()` and `status_porcelain()` APIs in `git.py`; pre-existing; Phase 2 only adds `status_porcelain`. Consolidation belongs in a dedicated `git.py` cleanup outside this phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate in a dedicated `git.py` cleanup outside this phase.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_1: [OUT_OF_SCOPE] Phase 7 may assume RST `commit_changelog` works
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: RST `commit_changelog` deferred to Phase 7 while RST text ops exist; Phase 7 driver may assume `.rst` commit works when only Markdown commit path exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Track Phase 7 task for RST `commit_changelog` or document API limitation in module docstring.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] `_rst_second_title_index` sentinel `0` matches bash
- **Reviewer(s)**: dyn-changelog-text-logic-output.txt
- **Severity**: nit
- **Concern**: Same sentinel as bash; callers guard with `second2 > 0`; no functional bug found.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_11: [OUT_OF_SCOPE] `idx > anchor + 1` skips anchor underline by design
- **Reviewer(s)**: dyn-changelog-text-logic-output.txt
- **Severity**: nit
- **Concern**: Intentionally skips anchor underline when choosing next generic RST title; consistent with title-line indexing.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_12: [OUT_OF_SCOPE] `_write_md_entry` double-call path does not double-insert
- **Reviewer(s)**: dyn-changelog-text-logic-output.txt
- **Severity**: nit
- **Concern**: Fallback does not stack two inserts on one buffer; no defect found.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Summary**: 25 in-scope merged findings; 12 out-of-scope (`OOS_1`–`OOS_12`). Highest-impact clusters: untracked `bump_worktree.py` (FINDING_1), RST/commit surface gaps (FINDING_7, FINDING_23), `commit_changelog` failure-path staging (FINDING_20), classify-bump and changelog commit parity test holes (FINDING_9, FINDING_11, FINDING_23), and RST insert logic without release sections (FINDING_25). Dyn-changelog “no bug” OOS notes are retained for voter context without suggested fixes where none were given.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] `python-tests` workflow does not pin bash/git/gawk
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `python-tests` does not explicitly install git/bash/gawk; future runner image change could skip many parity tests via `skipif`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add explicit apt install or smoke step asserting bash, git, gawk available.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] `ShipError` may include full git argv
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Uncaught `ShipError` could leak sensitive path literals in argv to stdout/stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Redact argv in operator-facing `ShipError` paths or avoid `_ensure_success` for sensitive ops.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Bash leaves CHANGELOG modified on commit failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-existing bash behavior: `commit-changelog.sh` leaves CHANGELOG modified on commit failure (no restore). Python partial restore can worsen index vs worktree (see in-scope FINDING_20).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address via Python fix above; optional bash alignment separately.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] `apply_bump` git commit is not path-scoped (`--only`)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Pre-existing bash parity; mitigated by clean-tree precheck. No change required for Phase 2; optional `--only` in Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: No change required for Phase 2; optional `--only` in Phase 7.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_6: [OUT_OF_SCOPE] UTF-8 sort matches `LC_ALL=C` for ASCII bump paths
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: UTF-8 byte sorting matches `LC_ALL=C` for ASCII paths (common bump set) and is tested in `test_version_bump.py:999-1019`; non-ASCII edge cases remain theoretically locale-sensitive in bash-only callers.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] Parity tests normalize boolean KV with `.lower()`
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: Parity tests bridge Python `True`/`False` and bash `true`/`false` correctly; not a defect.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] `_git_subprocess_env` mitigates locale for Guard 4 re-sort
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: Environment setup covers rebase/reset parity; Guard 4 comparisons re-sort in Python before equality, mitigating locale concern for those paths.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] Inherited exact-line dedupe in auto-resolve
- **Reviewer(s)**: dyn-changelog-text-logic-output.txt
- **Severity**: nit
- **Concern**: `seen` line dedupe matches bash `auto-resolve-changelog.sh`; inherited semantics, not a Python regression.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

