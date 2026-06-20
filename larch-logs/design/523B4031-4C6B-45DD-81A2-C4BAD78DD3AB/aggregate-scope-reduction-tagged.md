### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:212-217,Makefile:237-238,python/test_check_main_sync.py:1-107
- **Concern**: [SCOPE-REDUCTION] Makefile/test plan targets check-main-sync coverage via python/test_git.py even though python/test_check_main_sync.py already owns that CLI surface. Scenario: Deleting scripts/test-check-main-sync.sh and repointing make test-check-main-sync to ad hoc test_git.py -k cases duplicates existing tests and omits bash-harness cases not yet in pytest (mixed flush+non-flush block, dirty-tree reset refusal)
- **Proposed resolution**: Repoint make test-check-main-sync to python3 -m pytest python/test_check_main_sync.py -q; add an explicit ### UPDATED: python/test_check_main_sync.py row to audit scripts/test-check-main-sync.sh and port only missing cases there (not test_git.py)

### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:204,389-396
- **Concern**: [SCOPE-REDUCTION] Plan preserves exact retired script path literals in the static implement harness. Scenario: After the retired helpers are appended to python/migrated-scripts.tsv, make lint-retired-scripts will flag the kept forbid and fabricated-path strings, so the required make lint gate fails
- **Proposed resolution**: Revise the plan to update these guards too: build retired needles from split string pieces or replace them with path-clean assertions, and do not keep exact retired-path literals
