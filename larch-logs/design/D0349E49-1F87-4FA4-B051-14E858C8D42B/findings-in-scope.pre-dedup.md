### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_residual_bash.py:36-47
- **Concern**: `test_residual_bash.py` cleanup lists only `lib-plan-optional-trailers.sh` for orchestration-set removal although `lib-implement-clone-tag.sh` is also deleted and manifest-listed. Scenario: After `migrated-scripts.tsv` append, `make lint-retired-scripts` greps tracked files for the full retired path; the unsplit `skills/implement/scripts/lib-implement-clone-tag.sh` literal in `test_manifest_excludes_non_residual_orchestration` can still fail CI even when wrappers and docs are updated
- **Proposed resolution**: Add `skills/implement/scripts/lib-implement-clone-tag.sh` to the explicit orchestration-set drop list in the `### UPDATED: python/test_residual_bash.py` step (failure modes already name both paths; the file step should too)



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_residual_bash.py:36-47
- **Concern**: test_residual_bash.py drop list omits lib-implement-clone-tag.sh while failure modes require both retired libs removed. Scenario: Failure modes (plan.txt:280) require no unsplit manifest-listed retired-path literals in this fixture, but the Files section only names dropping lib-plan-optional-trailers.sh (plan.txt:240-241). Leaving skills/implement/scripts/lib-implement-clone-tag.sh in orchestration after manifest append makes make lint-retired-scripts grep the unsplit literal and fail CI
- **Proposed resolution**: Add lib-implement-clone-tag.sh to the explicit drop list in the python/test_residual_bash.py section (remove the unsplit literal entirely; do not split-at-boundary for deleted paths)



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_residual_bash.py:36-47
- **Concern**: Explicit drop list for deleted orchestration literals omits lib-implement-clone-tag.sh. Scenario: The plan's test_residual_bash.py section lists only skills/design/scripts/lib-plan-optional-trailers.sh under "Drop orchestration-set entries," but skills/implement/scripts/lib-implement-clone-tag.sh is also deleted, manifest-listed, and still present as an unsplit literal at line 42. Failure modes (lines 280-292) mention both paths, but the incomplete bullet makes it easy to drop only one entry and leave the clone-tag literal; make lint-retired-scripts then fails after migrated-scripts.tsv append.
- **Proposed resolution**: Add skills/implement/scripts/lib-implement-clone-tag.sh to the explicit "Drop orchestration-set entries" bullet (remove the unsplit literal entirely; do not split-and-keep). Keep the existing general rule that no manifest-listed retired path may remain as a full literal anywhere in the file.



### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_residual_bash.py:36-47
- **Concern**: `test_manifest_excludes_non_residual_orchestration` Drop list names only `lib-plan-optional-trailers.sh` while `lib-implement-clone-tag.sh` is also deleted and manifest-listed. Scenario: Failure modes require removing unsplit literals for both retired libs, but the explicit Drop bullet omits `skills/implement/scripts/lib-implement-clone-tag.sh`. An implementer can drop only the design lib, leave the clone-tag literal at line 42, and `make lint-retired-scripts` fails after manifest append
- **Proposed resolution**: Add `skills/implement/scripts/lib-implement-clone-tag.sh` to the mandatory Drop list in the `python/test_residual_bash.py` section (or split/remove both orchestration literals per `docs/python-migration.md`)



