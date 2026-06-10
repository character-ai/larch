### OOS_1: [OUT_OF_SCOPE] DESIGN_TMPDIR is not exported to the Python child
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-deployment-risk-output.txt
- **Severity**: latent
- **Concern**: `design-log-publish.sh` assigns `DESIGN_TMPDIR` from `--design-tmpdir` but does not export or explicitly pass it to the Python bridge, so direct/manual/harness invocations can make Python `quiet_init` fall back to `TMPDIR` and split quiet logs away from the parent’s design tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add export DESIGN_TMPDIR after validation, or prefix the python3 bridge with DESIGN_TMPDIR="$DESIGN_TMPDIR".
  - From cursor-specialist-edge-cases-output.txt: Prefix python3 with DESIGN_TMPDIR="$DESIGN_TMPDIR" or export DESIGN_TMPDIR after validation
  - From cursor-specialist-testing-output.txt: `export DESIGN_TMPDIR` (or prefix the `python3` line with `DESIGN_TMPDIR="$DESIGN_TMPDIR"`) immediately before the bridge block for direct-call robustness.
  - From dyn-deployment-risk-output.txt: Add `export DESIGN_TMPDIR` immediately after argv validation (once the directory check passes), matching other design scripts such as `skills/design/scripts/design-init-runparams.sh`.


### OOS_2: [OUT_OF_SCOPE] captured bridge stderr is not surfaced on failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-deployment-risk-output.txt
- **Severity**: latent
- **Concern**: `design-log-publish.sh` redirects Python bridge stderr to `design-log-ship.stderr.log`, but failure paths do not read, tail, redact, or mention that file, leaving operators with generic failure diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Pmention $_dlship_stderr_log in larch_err when non-empty
  - From dyn-deployment-risk-output.txt: On failure, tail/redact `"$_dlship_stderr_log"` into `larch_err` (with a byte cap, mirroring other diagnostic helpers) and mention the file path explicitly so operators know where to look.


