### FINDING_1: Pre-deletion parity gate is not mechanically runnable
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The testing strategy says to run retired `scripts/test-dispatch-with-waterfall.sh` once against the new verb, but every harness case hardcodes `$REPO_ROOT/scripts/dispatch-with-waterfall.sh`. After the script is deleted (or before a forwarder exists), that gate cannot run as written, so parity may be assumed without execution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace the parity-gate bullet with an explicit procedure: either (a) temporarily install a forwarder at `scripts/dispatch-with-waterfall.sh` that execs `python3 "$PLUGIN_ROOT/python/cli.py" agent dispatch-waterfall`, run the harness, then delete both; or (b) declare `python/test_agent_waterfall.py` the sole parity authority and drop the retired-harness rerun step.

### FINDING_2: `dispatch-code-voters.sh` cutover omits stale failure prose
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan repoints only the invocation and says "No other behavior change", but the non-zero path still logs `dispatch-with-waterfall.sh exited` at `scripts/dispatch-code-voters.sh:153`. Operators and log triage will see a deleted entrypoint name after cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the `### UPDATED: scripts/dispatch-code-voters.sh` step to reword the `larch_err` at line 153 to `agent dispatch-waterfall` (keep `set +e` / `set -e` semantics unchanged).

### FINDING_3: Decompose waterfall argv pseudocode conflates `os.environ.get` default with override-only seam
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Concern**: The plan says `waterfall_argv = [env] if env else [python3, cli, agent, dispatch-waterfall]` while today both call sites use `waterfall = os.environ.get(DECOMPOSE_*_WATERFALL_SH, <default path>)` then `cmd = [waterfall, ...]`. After copy-paste, `get` still supplies a truthy default string so the `python3/cli/agent/dispatch-waterfall` branch never runs and `subprocess.run` keeps invoking the deleted `scripts/dispatch-with-waterfall.sh` path (or a one-string ENOENT) instead of the new verb.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Split override detection from default: if DECOMPOSE_PANEL_WATERFALL_SH / DECOMPOSE_AGGREGATE_WATERFALL_SH in os.environ then waterfall_argv = [that value]; else waterfall_argv = [sys.executable or python3, str(PLUGIN_ROOT / python/cli.py), agent, dispatch-waterfall]. Add/adjust python/test_decompose.py to assert the default argv shape when the env vars are unset.

**Codebase corroboration (read-only):** Current `decompose.py` at lines 460–461 and 610–611 uses `os.environ.get(..., str(PLUGIN_ROOT / "scripts" / "dispatch-with-waterfall.sh"))` with a single-string `cmd`. `dispatch-code-voters.sh` line 153 still names `dispatch-with-waterfall.sh` in its `larch_err`. The harness hardcodes the bash script path throughout (e.g. `test-dispatch-with-waterfall.sh` line 129 onward).
