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
