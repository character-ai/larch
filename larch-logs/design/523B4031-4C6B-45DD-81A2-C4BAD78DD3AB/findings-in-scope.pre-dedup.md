### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:212-217,Makefile:237-238,python/test_check_main_sync.py:1-107
- **Concern**: [SCOPE-REDUCTION] Makefile/test plan targets check-main-sync coverage via python/test_git.py even though python/test_check_main_sync.py already owns that CLI surface. Scenario: Deleting scripts/test-check-main-sync.sh and repointing make test-check-main-sync to ad hoc test_git.py -k cases duplicates existing tests and omits bash-harness cases not yet in pytest (mixed flush+non-flush block, dirty-tree reset refusal)
- **Proposed resolution**: Repoint make test-check-main-sync to python3 -m pytest python/test_check_main_sync.py -q; add an explicit ### UPDATED: python/test_check_main_sync.py row to audit scripts/test-check-main-sync.sh and port only missing cases there (not test_git.py)



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/lib-phantom-probe.sh:57-60
- **Concern**: Planned cli.py delegation omits LARCH_QUIET_DISABLE=1 that today's check-phantom-dirty.sh call uses. Scenario: step-2-post-dispatch.sh sources lib-quiet.sh; lib-phantom-probe captures probe output via stdout command substitution. Without LARCH_QUIET_DISABLE=1, inherited quiet routing can send PHANTOM_* KVs to fd 3 instead of stdout, leaving ph_out empty and PHANTOM_STATUS unknown on the Step 2 post-dispatch path
- **Proposed resolution**: Wrap the new call exactly like today: LARCH_QUIET_DISABLE=1 python3 "$_phantom_plugin_root/python/cli.py" git phantom-probe --step "$step_token" (and document the requirement in scripts/lib-phantom-probe.md)



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/git.py:1239-1290
- **Concern**: Fail-open argv handling for snapshot-untracked and check-remote-branch still uses argparse _parse and collapses parse errors into generic missing-arg output. Scenario: After cutover, check-remote-branch --bogus emits ERROR=--branch is required instead of ERROR=unknown flag: --bogus; snapshot-untracked --output without a value emits --output is required instead of --output requires a value, breaking bash fail-open contracts callers may rely on
- **Proposed resolution**: In python/git.py, replace argparse in snapshot_untracked_main and check_remote_branch_main with manual argv loops matching the bash helpers (same pattern as check_phantom_dirty_main); pin pytest cases for unknown flags, missing --branch, and --output without value before deleting the shell scripts



### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-phantom-probe.sh:57-60
- **Concern**: Repoint omits LARCH_QUIET_DISABLE=1 on the cli.py git phantom-probe subprocess. Scenario: Today check-phantom-dirty.sh is invoked with LARCH_QUIET_DISABLE=1 before stdout is parsed into PHANTOM_* keys. The plan replaces that call with cli.py git phantom-probe but does not carry the env override. Under an inherited quiet session contract KVs can miss the command-substitution capture and step-2-post-dispatch loses PHANTOM_* output.
- **Proposed resolution**: In ### UPDATED: scripts/lib-phantom-probe.sh require LARCH_QUIET_DISABLE=1 on the python3 … git phantom-probe invocation (same pattern as the current check-phantom-dirty.sh call).



### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:204,389-396
- **Concern**: [SCOPE-REDUCTION] Plan preserves exact retired script path literals in the static implement harness. Scenario: After the retired helpers are appended to python/migrated-scripts.tsv, make lint-retired-scripts will flag the kept forbid and fabricated-path strings, so the required make lint gate fails
- **Proposed resolution**: Revise the plan to update these guards too: build retired needles from split string pieces or replace them with path-clean assertions, and do not keep exact retired-path literals



