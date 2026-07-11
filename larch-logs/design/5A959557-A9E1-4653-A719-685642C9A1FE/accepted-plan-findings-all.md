### FINDING_1: Tier A helper invocation omits the required run ID
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-Auth Boundary, Codex-dyn-Auth Boundary
- **Severity**: major
- **Concern**: The planned Tier A shell-helper invocation adds `--trusted-root` but omits the required `--run-id`. The helper requires `--mutation-context`, `--run-id`, and `--trusted-root` together for non-dry-run calls. As a result, authorized Tier A filing paths can pass the Python pre-check but reach the shell helper without a run ID, which refuses with `missing-run-id`/`mutation-refused` before any GitHub mutation and prevents issue creation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In ### UPDATED: python/larch/design/design_terminal.py, add --run-id with the existing _run_id value to the Tier A file-issue subprocess argv alongside --trusted-root; extend test_design_lifecycle.py helper-argv capture to assert --run-id is present
  - From Codex-Arch: Add --run-id with the authoritative `LARCH_RUN_ID` read from the same `source-env.sh` context, and test that the complete authorization argument set reaches the helper
  - From Cursor-Innovation: Add --run-id with the same _run_id used in the Tier A dedup pre-check, and extend test_design_lifecycle argv capture to assert --run-id alongside --trusted-root
  - From Cursor-Pragmatic: In `### UPDATED: python/larch/design/design_terminal.py`, add `--run-id` with the same `_run_id` used for the Tier A dedup pre-check, plus `--trusted-root str(design_tmpdir)`, to the Tier A shell-helper argv. Extend `test_design_lifecycle.py` to assert both flags on captured helper argv.
  - From Codex-Pragmatic: Add `--run-id`, `str(_run_id)` to this helper invocation and require the planned argv test to assert all three authorization arguments
  - From Codex-Requirements: Add `--run-id`, `_run_id` to the helper argv and assert both `--run-id` and `--trusted-root` in the lifecycle test
  - From Cursor-dyn-Auth Boundary: Add --run-id with the in-scope _run_id to the Tier A shell-helper argv alongside --trusted-root str(design_tmpdir); extend test_design_lifecycle.py helper-argv assertions and the plan grep step to require the full --mutation-context/--run-id/--trusted-root triple on every non-dry-run helper caller
  - From Codex-dyn-Auth Boundary: Add --run-id, using the authoritative run ID already read for this terminal path, alongside --trusted-root str(design_tmpdir); add an argv assertion for both required authorization values


### FINDING_2: Harness refusal cases omit or misconfigure trusted-root
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: minor
- **Concern**: Manual helper invocations in the cross-repository test harness are not consistently updated for the new required `--trusted-root` contract. Invalid-context, refusal-loop, test-denied, and copied-validator paths may now fail for missing or non-canonical trusted-root reasons instead of exercising their intended run-identity, containment, or denial semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In ### UPDATED: scripts/test-file-failure-report-cross-repo.sh, pass --trusted-root "$(dirname "$LIVE_CONTEXT")" on every non-dry-run SCRIPT invocation; for invalid-context keep a pinned canonical trusted root while the context file stays outside that root so containment failure remains the exercised refusal mode
  - From Cursor-Innovation: Retarget invalid-context to pass a canonical --trusted-root with a mismatched context run id; keep a separate missing-trusted-root case; pass --trusted-root on the copied-validator invocation at line 257
  - From Cursor-Pragmatic: Update the refusal matrix: pass a canonical `--trusted-root` for the harness session dir, and keep a separate outside-root negative case (already planned) plus an in-root context with wrong run id to preserve run-identity coverage.


