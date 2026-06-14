### OOS_4: risk-integration: python/test_implement_dispatch.py:788-804
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] FORKED_TARGET=true carve-out for main-branch guard (old Test 19c) has no pytest coverage. --forked /implement on main could incorrectly emit main-branch-prohibited and never launch Codex/Cursor. Add a main-branch test with FORKED_TARGET=true and a stub launcher; assert launcher runs and main-branch-prohibited is absent.
- **Suggested revision**: Address the concern above.


### OOS_5: risk-integration: python/test_implement_dispatch.py:534-631
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Codex/Cursor launcher missing-input-file and parent-mismatch reject paths from deleted test-codex-implementer.sh are not ported. Argv validation regressions could let launchers proceed with missing plan/feature/agent files or mismatched manifest/qa parents. Port deleted harness reject cases with pinned exit code 2 and literal stderr messages.
- **Suggested revision**: Address the concern above.


### OOS_6: **risk-integration** `python/implement_dispatch.py:114-120` — **Important** `_current_cli_path()` prefers ambient `LARCH_CLAUDE_PLUGIN_ROOT` over the `CLAUDE_PLUGIN_ROOT` that `run_dispatch_main()` just resolved for this run, so Step 2 can launch child CLI verbs from a stale plugin checkout. Scenario: `larch-run.sh` resolves the current plugin in `CLAUDE_PLUGIN_ROOT`, but the operator shell still has `LARCH_CLAUDE_PLUGIN_ROOT` pointing at an older installed plugin; `_run_launcher()` then invokes that old `python/cli.py`, which may not have `agent launch-codex-implement`, causing a false `wrapper-validation-failure` or old behavior. **Suggested fix:** Prefer `CLAUDE_PLUGIN_ROOT` over `LARCH_CLAUDE_PLUGIN_ROOT` in `_current_cli_path()`, or pass the already resolved `plugin_root` through to every child CLI invocation.
- **Reviewer**: codex-generic-output.txt
- **Concern**: - **risk-integration** `python/implement_dispatch.py:114-120` — **Important** `_current_cli_path()` prefers ambient `LARCH_CLAUDE_PLUGIN_ROOT` over the `CLAUDE_PLUGIN_ROOT` that `run_dispatch_main()` just resolved for this run, so Step 2 can launch child CLI verbs from a stale plugin checkout. Scenario: `larch-run.sh` resolves the current plugin in `CLAUDE_PLUGIN_ROOT`, but the operator shell still has `LARCH_CLAUDE_PLUGIN_ROOT` pointing at an older installed plugin; `_run_launcher()` then invokes that old `python/cli.py`, which may not have `agent launch-codex-implement`, causing a false `wrapper-validation-failure` or old behavior. **Suggested fix:** Prefer `CLAUDE_PLUGIN_ROOT` over `LARCH_CLAUDE_PLUGIN_ROOT` in `_current_cli_path()`, or pass the already resolved `plugin_root` through to every child CLI invocation.
- **Suggested revision**: Address the concern above.


### OOS_7: **correctness** `python/implement_dispatch.py:455-462` — **Important** The submodule dirty-path scan parses NUL porcelain records with a simple split and does not skip the second path of rename/copy records. Scenario: with a submodule at `vendor`, a normal repo rename like `oldvendor/foo.txt -> renamed.txt` yields a second NUL record `oldvendor/foo.txt`; slicing `rec[3:]` turns it into `vendor/foo.txt`, so the dispatcher can falsely bail `submodule-dirty` after a valid implementation. **Suggested fix:** Reuse the indexed porcelain parser pattern from `_parse_porcelain_z()` here, including the `R`/`C` second-path skip, before checking `_path_under_submodule()`.
- **Reviewer**: codex-generic-output.txt
- **Concern**: - **correctness** `python/implement_dispatch.py:455-462` — **Important** The submodule dirty-path scan parses NUL porcelain records with a simple split and does not skip the second path of rename/copy records. Scenario: with a submodule at `vendor`, a normal repo rename like `oldvendor/foo.txt -> renamed.txt` yields a second NUL record `oldvendor/foo.txt`; slicing `rec[3:]` turns it into `vendor/foo.txt`, so the dispatcher can falsely bail `submodule-dirty` after a valid implementation. **Suggested fix:** Reuse the indexed porcelain parser pattern from `_parse_porcelain_z()` here, including the `R`/`C` second-path skip, before checking `_path_under_submodule()`.
- **Suggested revision**: Address the concern above.


