## Goal
Implement issue #5923: [IMPLEMENTING] [BUG] TMPDIR scratch-dir/log leak: bypasses run-scoped tmpdirs, never cleaned up.

## Implementation Plan
## Summary

At least 6 independent call sites across the larch codebase create scratch directories/files directly at the root of the macOS per-user `$TMPDIR` via bare `tempfile.mkdtemp()`/`tempfile.mkstemp()`, instead of nesting them under the existing per-run scratch directories (`review_tmpdir`, `design_tmpdir`/`DESIGN_TMPDIR`, `IMPLEMENT_TMPDIR`) that this codebase already uses elsewhere. Most of them are also never cleaned up. On a live dev machine this produced 89,510 top-level `$TMPDIR` entries, of which over 95% were attributable to larch itself. This directly caused the #5868 hook-timeout symptom (already patched by scoping the hook's scan and raising its timeout), but that patch only narrowed what the hook scans — it does not stop the underlying growth, which will make hook scans slow again as `$TMPDIR/larch-*` keeps growing.

## Original report

Investigation performed 2026-06-30 on a live dev machine found `$TMPDIR` (`/var/folders/.../T/`) had grown to 89,510 top-level entries. Breakdown and root causes, each confirmed by reading the source:

1. `larch-tally-blocks-*` (55,738 entries, 62% of total) — `python/larch/review/review_tally.py:209`, `tempfile.mkdtemp(prefix="larch-tally-blocks-")` inside `_block_files(ballot_file: Path) -> list[Path]`. No cleanup anywhere in the file. Still actively leaking at investigation time: oldest observed dir mtime 2026-06-17 22:14, newest essentially "now" (2026-06-30 23:23) — roughly 13 days of continuous accumulation at ~4,300 leaked dirs/day.
2. `larch-report-tokens.*` (10,866 entries, 12%) — `python/larch/report/report_tokens_cli.py:66` and `report_tokens_render.py:219`, both `tempfile.mkdtemp(prefix="larch-report-tokens.")`. No cleanup in either file. Populated with real content (`report-cache.ndjson`, plot output).
3. `larch-cursor-cfg-*` (4,647 entries, 5%) — four call sites: `_review_launcher.py:858`, `_ci_launcher.py:343` and `:802`, `_auth.py:325`, all `tempfile.mkdtemp(prefix="larch-cursor-cfg-")`. Unlike 1-2, all four DO wrap the directory in `try/finally: shutil.rmtree(cfg_tmp, ignore_errors=True)`. Despite that, thousands still leak — implying the owning process is killed (SIGKILL/timeout) before the `finally` runs.
4. `larch-sweep-design-logs-*.log` (2,005 entries, 2%) — `scripts/sweep-design-logs.sh:17`, a `SessionStart` hook that runs on every Claude Code session start and writes a per-invocation debug log with no expiry.
5. `larch-validate-plan-commands.log.*` (~1,024+ of a ~2,860 bucket) — `python/larch/design/_plan_quality_commands.py:887`, `tempfile.mkstemp(prefix="larch-validate-plan-commands.log.", dir=ctx.tmpdir or "/tmp")`, reached only when no `/design`-session directory is available at call time.
6. `larch-quiet-*.log` (1,748 entries, 2%) — template in `python/larch/core/config.py:469`, written e.g. by `scripts/sessionstart-health.sh:26`. A cleanup mechanism exists (`python/larch/report/cleanup_implement_logs.py` Action 7) but only sweeps quiet-logs nested inside an active `/implement` session's own `breadcrumbs/` directory; top-level/no-session writes are never swept.

A one-time manual mitigation (age-gated deletion, entries older than 24h only, restricted to exactly these 6 confirmed-safe patterns) removed 74,899 of the 89,510 entries, leaving 14,628. This is a stopgap; the root causes are unfixed and will reaccumulate at the same rate.

## Reproduction scenario

Direct empirical observation on a live dev machine (see counts above) is the primary evidence. To reproduce the growth pattern: repeatedly run any `/implement` Step 5 review-tally sequence (exercises `review_tally.py`'s ballot-splitting path), or repeatedly run `/report-tokens analyze`, or repeatedly run `python3 python/cli.py plan validate` **outside** of an active `/design` session (no `DESIGN_TMPDIR` set), then inspect `$TMPDIR` for accumulating `larch-tally-blocks-*` / `larch-report-tokens.*` / `larch-validate-plan-commands.log.*` entries that never disappear.

## Expected behavior

Scratch directories/files created for one run should either (a) live inside that run's existing per-run tmpdir (`review_tmpdir` / `design_tmpdir` / `IMPLEMENT_TMPDIR`), so garbage-collecting the run is a single `rm -rf` of one directory, or (b) if no run context exists, be cleaned up when the owning process exits, or expire via a periodic age-based sweep. `$TMPDIR`'s top level should not grow unboundedly.

## Observed behavior

89,510 top-level `$TMPDIR` entries observed, growing continuously (review_tally.py's dirs alone at ~4,300/day). Over 95% attributable to larch's own scratch-file creation, scattered directly at `$TMPDIR`'s root rather than nested under any run-scoped directory.

## Root cause analysis

The per-run subdirectory concept already exists in this codebase and works correctly wherever it's actually threaded through. The leak sites fall into four distinct causal buckets, each confirmed by reading the code (not inferred):

1. **Not wired through a function boundary (single biggest contributor, `review_tally.py`).** The function that calls `_block_files(ballot_file)` (around line 636) already has `review_tmpdir: Path` as a local variable in scope, and uses it directly for several other output files in the same function (`accepted-findings.md`, `rejected-findings.md`, `voting-tally.md`, etc. — see lines 622-628). But `_block_files`'s signature is `_block_files(ballot_file: Path) -> list[Path]` — no directory parameter at all — so it has no way to nest under `review_tmpdir` even though the caller has it right there. This is a plumbing gap, not a design decision.

2. **Fallback branch with no expiry (`_plan_quality_commands.py`).** `validate_plan_main` correctly nests under `design_tmpdir` when a `/design` session is live: `if ok and design_tmpdir and design_tmpdir.is_dir(): log_path = design_tmpdir / "validate-plan-commands.log"` (no leak in this branch). It only falls into `tempfile.mkstemp(dir=ctx.tmpdir or "/tmp")` — `ctx.tmpdir` here reflects the ambient `Ctx.from_mapping({**os.environ, ...})`, i.e. essentially the bare OS `$TMPDIR` — when `design_tmpdir` is unavailable or fails `validate_design_tmpdir()`, e.g. a standalone/CI invocation of `plan validate` with no active `/design` session. The branching logic itself is sound; only that fallback branch lacks any cleanup or expiry.

3. **Tool operates across many runs, not inside one (`report_tokens_cli.py` / `report_tokens_render.py`).** `/report-tokens` analyzes potentially thousands of already-committed historical run logs in a single invocation; it is not a step "inside" any single design/implement run, so there is no existing run directory to nest under. Its own `temp_root` is arguably its own self-contained unit — the actual defect is that it's never removed when the CLI process exits (no `try/finally`, no `TemporaryDirectory()` context manager).

4. **Cleanup exists but doesn't survive abrupt termination (`larch-cursor-cfg-*`).** All four call sites already wrap the directory in `try/finally: shutil.rmtree(...)`. Leaks persisting despite this implies the owning process is being hard-killed (SIGKILL, an outer `timeout` wrapper, or an abandoned/interrupted Claude Code session) before Python's `finally` gets a chance to execute. This is a resilience gap, not a missing-cleanup-code gap.

## Evidence

- `python/larch/review/review_tally.py:208-214`: `_block_files(ballot_file: Path) -> list[Path]` — no directory parameter; body is `block_dir = Path(tempfile.mkdtemp(prefix="larch-tally-blocks-"))` with no matching `rmtree` anywhere in the file.
- `python/larch/review/review_tally.py:602-657`: enclosing function already declares and uses `review_tmpdir = Path(args.review_tmpdir)` for multiple other output files, then calls `blocks = _block_files(ballot_file)` at line 636 without passing `review_tmpdir` through.
- `python/larch/design/_plan_quality_commands.py:873-891`: full branch showing the correct in-session nesting path (`design_tmpdir / "validate-plan-commands.log"`) versus the uncleaned fallback (`tempfile.mkstemp(..., dir=ctx.tmpdir or "/tmp")`).
- `python/larch/report/report_tokens_cli.py:66`: `temp_root = Path(tempfile.mkdtemp(prefix="larch-report-tokens."))` inside `main()`, used later for `report-cache.ndjson` and plot output (lines 77, 96, 98), never removed.
- `python/larch/agents/_review_launcher.py:857-865,868-869,1121,1149-1150`: `_review_setup_cursor_config_dir()` / `_review_cleanup_cursor_config_dir()` with a correct `try/finally` wrapping at the call site — confirms cleanup code exists, contradicting a naive "missing cleanup" explanation for this specific pattern.
- Empirical counts and age range from direct filesystem inspection: 55,738 / 10,866 / 4,647 / 2,005 / 1,748 / ~1,024+ entries respectively; oldest `larch-tally-blocks-*` mtime 2026-06-17, newest 2026-06-30 (same day as investigation).

## Affected files

- `python/larch/review/review_tally.py` — `_block_files` (no dir param; root cause bucket 1)
- `python/larch/report/report_tokens_cli.py` — `main()` (no cleanup; root cause bucket 3)
- `python/larch/report/report_tokens_render.py` — `render()` (no cleanup; root cause bucket 3)
- `python/larch/agents/_review_launcher.py` — `_review_setup_cursor_config_dir` / `_review_cleanup_cursor_config_dir` (cleanup exists but doesn't survive kill; root cause bucket 4)
- `python/larch/agents/_ci_launcher.py` — two equivalent cursor-cfg call sites (same as above)
- `python/larch/agents/_auth.py` — `_CursorProbeSetup` / `_cursor_probe_cleanup_private_config_dir` (same as above, probe context)
- `scripts/sweep-design-logs.sh` — per-SessionStart debug log with no expiry
- `python/larch/design/_plan_quality_commands.py` — `validate_plan_main` (root cause bucket 2)
- `python/larch/core/config.py` — `PATH_QUIET_LOG_TEMPLATE` (line 469)
- `python/larch/report/cleanup_implement_logs.py` — existing quiet-log sweep, scoped too narrowly (session-breadcrumbs only)

## Suggested fix(es)

1. Thread `review_tmpdir` (or a stable subdirectory of it, e.g. `review_tmpdir / "tally-blocks"`) into `_block_files` as a `dir=` argument to `tempfile.mkdtemp`, since the caller already has `review_tmpdir` in scope. This alone addresses 62% of the observed leak.
2. Give `_plan_quality_commands.py`'s no-session fallback branch the same lifecycle treatment as the in-session path: either clean up immediately after use, or route it to a single well-known location that an existing/new periodic sweep already targets, instead of scattering directly at `$TMPDIR`'s root.
3. Wrap `report_tokens_cli.py`'s `temp_root` and `report_tokens_render.py`'s equivalent in `tempfile.TemporaryDirectory()` (or an explicit `try/finally: shutil.rmtree`) so it is removed when the CLI invocation ends.
4. For the four `larch-cursor-cfg-*` call sites, investigate what is hard-killing the owning process before `finally` runs (outer `timeout` wrapper vs. abandoned session vs. something else), and consider a periodic age-based reaper as a backstop independent of in-process cleanup, e.g. generalizing whatever `/larch:cleanup` already does for stale session directories to also cover this pattern.
5. Bound `scripts/sweep-design-logs.sh`'s per-invocation debug log (rotate, truncate, or nest inside an existing session tmpdir when one is live instead of a fresh per-PID file at the bare root).
6. Extend `cleanup_implement_logs.py`'s quiet-log sweep (or add a parallel mechanism) to also cover top-level/no-session quiet-log writes.
7. Architectural option covering all of the above at once: introduce one common umbrella directory (e.g. `$TMPDIR/larch/` or a `~/.cache/larch/scratch/` root) that every one of these prefixes nests under regardless of call site, so a single cheap, well-known-location age-based sweep bounds total growth even for call sites that can't easily thread a specific run's directory through (e.g. standalone/CI invocations, cross-run analysis tools).

## Open questions

- Does `Ctx.tmpdir` (`python/larch/core/config.py`, constructed via `Ctx.from_mapping(...)`) ever resolve to something other than the bare OS `$TMPDIR`, or is it always just a passthrough of the `TMPDIR` env var? If the latter, using it as a fallback in `_plan_quality_commands.py` is equivalent to hardcoding the bare tmp root.
- What specifically kills the cursor-cfg-owning process before its `finally` executes? Needs direct instrumentation (e.g. temporarily logging PID/exit-reason) to confirm whether it's an outer `timeout` wrapper, an abandoned/interrupted Claude Code session, or something else.
- Should `/larch:cleanup`'s existing "stale session temp directories by age" sweep be generalized to also cover the non-session prefixes identified here, or should a separate periodic sweep own that instead?
- Is there a reason `report_tokens_cli.py` / `report_tokens_render.py` use bare `mkdtemp()` rather than `tempfile.TemporaryDirectory()`, given the directory's lifetime is scoped to the single CLI invocation?

## Test plan
(no test plan section in plan-file)
