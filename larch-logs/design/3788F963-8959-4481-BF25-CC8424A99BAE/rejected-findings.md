### [Plan Review] FINDING_4

### FINDING_4: `_promote_inner_done` not migrated to `LauncherPaths`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `_promote_inner_done` keeps inline `.inner.done`/`.done` suffix literals while `LauncherPaths` becomes the declared single owner of the sidecar file-family. The plan routes every promote hook through `_promote_inner_done(paths.output)` but does not migrate that helper to `LauncherPaths` fields. A future suffix tweak in the dataclass can desync promotion from every other migrated sidecar path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Rewrite `_promote_inner_done` to use `LauncherPaths.from_output(output).inner_done` and `.done` (or accept `LauncherPaths` directly); treat this as part of the migration, not call-site-only.


### [Plan Review] FINDING_6

### FINDING_6: Per-family epilogue order tests lack real launch-path verification
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Parameterized hook-list tests can pass while `launch_*_main` wires a different order; the refactor goal is preserving launcher tails, not just `_finalize_launch` iteration. Order fixtures should verify callee order inside real `launch_*_main` paths rather than maintaining parallel hook lists that can drift from production wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Require order fixtures to spy on _promote_inner_done _append_ci_failure _emit_ci_launcher_result _record_implement_timing etc during launch_codex_ci_main launch_cursor_ci_main and implement mains rather than maintaining parallel hook lists only in tests **1. [correctness / blocking]** Codex implement normative table (`plan.txt` lines 39–46) omits `_promote_inner_done`. Current code promotes at ```5118:5121:python/agents.py``` between failure append and emit. Revise the table and hook list to include promote as step 6. **2. [correctness / important]** Cursor implement normative table (`plan.txt` lines 48–54) omits `_record_implement_timing`. Current code records timing at ```5222:5224:python/agents.py``` between meta append and usage. Revise the table to insert timing as step 2. **3. [risk-integration / blocking]** `run_external_agent` stale cleanup at ```1747:1750:python/agents.py``` also removes optional `stdout_path` and `stderr_path`. The plan’s migration test scope (lines 188–192) covers only `LauncherPaths` fields plus `output`. Document and test preservation of conditional `stdout_path`/`stderr_path` cleanup. **4. [risk-integration / important]** Per-family order fixtures (lines 205–210) should verify callee order inside real `launch_*_main` paths (existing CI tests already monkeypatch launchers at ```2843:2908:python/test_agents.py```), not duplicate hook sequences that can drift from production wiring.


