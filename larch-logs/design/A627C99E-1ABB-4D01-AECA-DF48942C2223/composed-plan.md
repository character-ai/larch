## Plan

**Bug**: `python/larch/git/pr_body.py` builds the larch CLI path with `Path(__file__).resolve().parent / "cli.py"` at three sites. The module lives at `python/larch/git/`, so that resolves to the nonexistent `python/larch/git/cli.py` instead of `python/cli.py`. The diagram site (`agent launch-claude-subprocess`) fails loudly with `rc=2`; the two `check=False` sites (`plugin read-version`, `tracking-issue upsert-summary`) fail silently.

**Approach**:

- Add a module constant `_PY_CLI = Path(__file__).resolve().parents[2] / "cli.py"` (same idiom as `python/larch/state/bootstrap.py` and `python/larch/state/closeout.py`).
- Reuse `_PY_CLI` for all three larch CLI subprocess calls: `plugin read-version`, `tracking-issue upsert-summary`, `agent launch-claude-subprocess`.
- Preserve graceful degradation: diagram generation still returns a non-fatal failure tuple; metadata posting still returns its failure tuple; version lookup still falls back to `unknown`.
- Add bounded warnings on stderr only via `print(..., file=sys.stderr)`, never stdout. `post_tracking_issue_main` and `generate_code_flow_diagram_main` emit machine-parseable `KEY=value` rows via `_emit_kv`; warnings containing `=` on stdout could be mis-parsed as KV rows.
- Do not emit warnings on successful subprocess returns.

### UPDATED: python/larch/git/pr_body.py

- Add a module constant near the existing constants: `_PY_CLI = Path(__file__).resolve().parents[2] / "cli.py"`.
- Replace both inline `Path(__file__).resolve().parent / "cli.py"` uses in `post_tracking_issue`.
- Replace the diagram `plugin_root` local with `_PY_CLI` on the non-test-hook launch path.
- Before the non-test-hook diagram launch, if `not _PY_CLI.is_file()`, emit a bounded stderr warning with a stable label (e.g. `pr_body: cli.py not found at ...`).
- After `plugin read-version`, if `completed.returncode != 0`, emit a bounded stderr warning (stable prefix `pr_body: plugin read-version`) and keep `version = "unknown"`.
- Catch `OSError` at the version read site as today, but surface a bounded stderr warning instead of silently passing.
- After `tracking-issue upsert-summary`, if `completed.returncode != 0`, emit a bounded stderr warning (stable prefix `pr_body: tracking-issue upsert-summary`) and keep the current `(1, False, "", err)` return.

### UPDATED: python/test_pr_body.py

- Add a regression test asserting `pr_body._PY_CLI` resolves to the repository `python/cli.py` and exists.
- Update `test_post_tracking_issue_writes_metadata` (or add a sibling) with a `fake_run` that records argv per `subprocess.run` and asserts both larch CLI calls use `str(pr_body._PY_CLI)` as `argv[1]`.
- Add diagram argv coverage without `LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS`: a single `fake_run` that returns success for git argv prefixes (`git merge-base`, `git rev-parse`, `git diff`) and captures the launch argv on the CLI call; assert `launch_argv[1] == str(pr_body._PY_CLI)` and `launch_argv[2:4] == ["agent", "launch-claude-subprocess"]`.
- Add stderr-warning coverage for one nonzero `check=False` path (prefer `plugin read-version` nonzero): use `capsys`, assert a stable prefix in `.err` only, and confirm `.out` is free of warning text.
- Keep `test_generate_code_flow_diagram_uses_launcher_not_stub` intact for the override path.

### Edge cases and constraints

- Preserve the `LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS` override; it must still bypass `_PY_CLI`.
- Keep warnings bounded so subprocess stderr cannot flood run logs.
- Do not change `summary-metadata.md` contents except restoring the real plugin version when the CLI call succeeds.
- All new diagnostic output stays on stderr; stdout remains reserved for `_emit_kv` and other machine-parseable contracts.
- Scope is limited to these two files. A repo-wide grep confirms no other module carries the broken `.parent / "cli.py"` idiom; sites directly in `python/` (e.g. `oos_filer.py`, `final_report.py`) are already correct.

### Testing strategy

- `python3 -m pytest python/test_pr_body.py`.
- `make py-test` only if the targeted test exposes broader coupling.
- `make py-lint` for imports, private-constant access, or stderr formatting.

## Acceptance

- All three `cli.py` computations in `pr_body.py` resolve to `python/cli.py` via the shared `_PY_CLI` constant.
- `/implement` Step 7a code-flow diagram generation no longer fails with `rc=2` / "No such file or directory" for the CLI path.
- `plugin read-version` reads the real plugin version (not `unknown`); `tracking-issue upsert-summary` reaches `python/cli.py`.
- New warnings appear on stderr only; stdout stays free of warning text so `_emit_kv` rows are uncorrupted.
- The `LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS` override still bypasses `_PY_CLI`.
- Graceful degradation is preserved: no new hard crash of `/implement`.
- `python/test_pr_body.py` gains a `_PY_CLI`-resolves-to-existing-`python/cli.py` test, argv assertions that all three sites use `str(_PY_CLI)`, and stderr-warning coverage for one nonzero `check=False` path.
- `python3 -m pytest python/test_pr_body.py` passes; `make py-lint` is clean.

review_status: ok
rounds_completed: 2
diff_lines: 75
