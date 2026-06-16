### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:205-206;scripts/test-dispatch-with-waterfall.sh:129-910
- **Concern**: Pre-deletion parity gate is not mechanically runnable. Scenario: The testing strategy says to run retired `scripts/test-dispatch-with-waterfall.sh` once against the new verb, but every harness case hardcodes `$REPO_ROOT/scripts/dispatch-with-waterfall.sh`. After the script is deleted (or before a forwarder exists), that gate cannot run as written, so parity may be assumed without execution.
- **Proposed resolution**: Replace the parity-gate bullet with an explicit procedure: either (a) temporarily install a forwarder at `scripts/dispatch-with-waterfall.sh` that execs `python3 "$PLUGIN_ROOT/python/cli.py" agent dispatch-waterfall`, run the harness, then delete both; or (b) declare `python/test_agent_waterfall.py` the sole parity authority and drop the retired-harness rerun step.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:100-101;scripts/dispatch-code-voters.sh:142-153
- **Concern**: `dispatch-code-voters.sh` cutover omits stale failure prose. Scenario: The plan repoints only the invocation and says "No other behavior change", but the non-zero path still logs `dispatch-with-waterfall.sh exited` at `scripts/dispatch-code-voters.sh:153`. Operators and log triage will see a deleted entrypoint name after cutover.
- **Proposed resolution**: Extend the `### UPDATED: scripts/dispatch-code-voters.sh` step to reword the `larch_err` at line 153 to `agent dispatch-waterfall` (keep `set +e` / `set -e` semantics unchanged).

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/decompose.py:460-461,610-611
- **Concern**: Decompose waterfall argv pseudocode conflates os.environ.get default with override-only single-executable seam. Scenario: The plan says waterfall_argv = [env] if env else [python3, cli, agent, dispatch-waterfall] while today both call sites use waterfall = os.environ.get(DECOMPOSE_*_WATERFALL_SH, <default path>) then cmd = [waterfall, ...]. After copy-paste, get still supplies a truthy default string so the python3/cli/agent/dispatch-waterfall branch never runs and subprocess.run keeps invoking the deleted scripts/dispatch-with-waterfall.sh path (or a one-string ENOENT) instead of the new verb.
- **Proposed resolution**: Split override detection from default: if DECOMPOSE_PANEL_WATERFALL_SH / DECOMPOSE_AGGREGATE_WATERFALL_SH in os.environ then waterfall_argv = [that value]; else waterfall_argv = [sys.executable or python3, str(PLUGIN_ROOT / python/cli.py), agent, dispatch-waterfall]. Add/adjust python/test_decompose.py to assert the default argv shape when the env vars are unset.
