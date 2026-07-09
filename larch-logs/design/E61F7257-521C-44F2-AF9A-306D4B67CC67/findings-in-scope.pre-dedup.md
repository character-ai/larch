### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/test_progress_statusline.py
- **Concern**: Proposed unit test path violates flat-tests lint. Scenario: `python/larch/lint/lint_flat_tests.py` allows only `python/test_support.py` at `python/` root; `make py-lint` / pre-commit will fail before the feature lands
- **Proposed resolution**: Place tests at `python/tests/report/test_progress_statusline.py` (or extend `python/tests/report/test_progress_report.py`) and update the Testing strategy command accordingly



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py
- **Concern**: Compact statusline omits ship-pr phase rendering contract. Scenario: `_render_implement` routes live Step 8+ waits through `ship-pr-state.sh` / `_render_ship_pr` (PHASE, stall step, PR); timing marks alone stay at coarse labels like `Step 8 — ship PR` and miss sub-phase churn the bug report highlights
- **Proposed resolution**: Add a compact ship-pr branch: when `ship-pr-state.sh` exists for the strict-live candidate, surface `PHASE` (and stall/PR fields when set) on line 1 instead of only the latest timing mark



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/_progress_report_live.py
- **Concern**: Compact renderer may reuse `_render_generic` / `_last_artifact`. Scenario: `_render_generic` always appends `_last_artifact(tmpdir)`, which prints repo-relative paths under the tmpdir and can span two lines; plan edge cases forbid tmpdir path leakage and whitespace-only output
- **Proposed resolution**: Define a statusline-only compact formatter (1–2 lines, yellow ANSI) that never calls `_last_artifact` or the full multi-section renderers; add a test that corrupt or stale ledgers cannot emit path fragments



### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/report/_progress_report_live.py
- **Concern**: Strict liveness discovery side effects not pinned. Scenario: `design_step6._step6_in_flight` calls `registry.unlink_entry` on dead rows; a statusline refresh every ~10s could reap registry rows still needed by foreground `bgjob wait` if discovery copies that pattern
- **Proposed resolution**: Document and implement strict discovery as read-only: scan `registry.iter_entries()`, match resolved `entry.tmpdir`, treat live when `child_liveness` or `daemon_liveness` is true and entry is not expired; never unlink or mutate registry during render



### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: security
- **Location**: python/larch/report/statusline_install.py
- **Concern**: Larch-owned `statusLine` detection left as “prefer”. Scenario: Weak ownership matching risks either refreshing a custom third-party command (clobber) or failing to refresh the launcher after plugin moves (stale `PLUGIN_ROOT`)
- **Proposed resolution**: Pin ownership: expanded `statusLine.command` equals `~/.cache/larch/statusline.sh` (or the configured cache launcher path); only that path may be installed/refreshed; all other commands are immutable



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:1239-1260
- **Concern**: Compact statusline omits ship-pr and design plan-review branches. Scenario: During Step 8+ ship-pr bgjob waits the timing mark can lag while ship-pr-state.sh holds the real phase; a compact renderer that only reads _latest_timing_mark shows the wrong step or omits PR/CI/stall fields
- **Proposed resolution**: Mirror _render_implement/_render_design routing in a dedicated compact helper: when ship-pr-state.sh exists emit a one-line ship-pr summary; when design plan-review is active emit round/reviewer counts without Gantt sections



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/_progress_report_live.py:215-239
- **Concern**: Stale-only annotation does not fix multi-pointer ranking for progress report. Scenario: _discover_live_run still picks max(mtime); a stale pointer with newer ledger activity beats a live lower-mtime run, so idle p/progress at chunk boundaries can print annotated but wrong data while the live run is hidden
- **Proposed resolution**: When any same-cwd candidate has live bgjob evidence prefer those candidates before mtime ranking for both strict statusline and progress report; keep the stale note only for the selected pointer when it lacks registry proof



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/report/_progress_report_live.py:215-239
- **Concern**: [SCOPE-REDUCTION] Pointer-glob discovery scales with stale pointer pile. Scenario: Statusline refresh every ~10s globbing all current-*-env-*.sh can scan 1000+ stale files (observed in run logs) before liveness checks
- **Proposed resolution**: For statusline strict discovery scan registry.iter_entries() for live rows whose CLONE_PATH matches cwd then resolve tmpdir/skill; use pointer glob only as fallback when no live registry row exists



### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/statusline_install.py
- **Concern**: Installer statusLine JSON shape underspecified. Scenario: Without pinning type command plus command plus refreshInterval the writer may emit settings Claude Code ignores or mis-parse
- **Proposed resolution**: Pin the exact statusLine object written (match repo probe: type command command refreshInterval) and test round-trip parse in test_progress_statusline.py



### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: SECURITY.md:246-248
- **Concern**: SECURITY.md SessionStart inventory not updated for new hook. Scenario: Existing paragraphs enumerate sessionstart-health cleanup-sessionstart and sweep-design-logs; adding sessionstart-statusline.sh without updating those sections leaves security docs wrong about SessionStart mutation surface
- **Proposed resolution**: Add a SessionStart statusline installer paragraph listing files written (~/.cache/larch/statusline.sh and user settings.json statusLine only when absent or larch-owned) no-clobber rules and hook ordinal relative to existing SessionStart hooks



### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:322-324
- **Concern**: Compact renderer must not reuse _last_artifact. Scenario: _render_generic second line can expose tmpdir-relative artifact paths and blow the 1-2 line budget
- **Proposed resolution**: Explicitly forbid _last_artifact and multi-section Gantt helpers in statusline_main; cap output to skill step elapsed plus optional round/reviewer or voter counts



### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:13-14,83-90
- **Concern**: Installer only updates `~/.claude/settings.json` and refuses to compose with any existing non-larch `statusLine`. Scenario: Any repo or user profile that already has a higher-precedence `statusLine` keeps shadowing the new launcher, so bgjob phases still have no zero-cost progress surface
- **Proposed resolution**: Detect the winning settings layer and either install there when larch-owned or provide a non-destructive composition path for an existing `statusLine` command



### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:1239-1260
- **Concern**: Compact statusline renderer omits implement ship-pr branch. Scenario: During Step 8 `implement-step8-ship` bgjob waits the full `_render_implement` path prefers `ship-pr-state.sh` over stale timing marks; a mark-only compact line can show Step 5 or Step 7a while CI/merge is running
- **Proposed resolution**: Mirror `_render_implement` routing in the compact path: when `ship-pr-state.sh` exists emit a one-line ship phase summary (phase, optional PR/iteration); keep review-round fields only on the Step 5 branch



### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/statusline_install.py:launcher-contract
- **Concern**: Fail-silent contract covers stdout only, not stderr. Scenario: Uncaught Python errors from `progress statusline` can print tracebacks into the Claude statusLine UI
- **Proposed resolution**: Add `2>/dev/null` to `~/.cache/larch/statusline.sh` and require `statusline_main` never write stderr on any path (outer `try/except` returns exit 0 with empty stdout)



### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/report/statusline_install.py:settings-write
- **Concern**: Settings installer lacks atomic write for `~/.claude/settings.json`. Scenario: A SessionStart kill mid-write can corrupt the entire user settings file, not just `statusLine`
- **Proposed resolution**: Use `larch_io.atomic_write` (or write-temp-then-rename) for settings.json updates; keep invalid-JSON fail-open before any write



### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: scripts/hook-bgjob-wait-progress.sh:matcher
- **Concern**: PostToolUse bgjob-wait matcher may miss production wait fences. Scenario: Production waits use `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py bgjob wait ...` and design-run launchers, not bare `python3 .../python/cli.py bgjob wait`; a narrow matcher would never emit chunk snapshots
- **Proposed resolution**: If the optional hook ships, match any Bash command containing `bgjob wait` with `--step` and `--tmpdir`, or normalize through the same launcher pattern skills use today



### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/report/statusline_install.py:1
- **Concern**: [SCOPE-REDUCTION] First-run SessionStart auto-installs a global statusLine instead of keeping installation opt-in. Scenario: The plan creates or rewrites ~/.claude/settings.json whenever no statusLine exists, so merely starting Claude with the plugin changes user-level UI state for all sessions and deletion is not a durable opt-out because the next SessionStart reinstalls it
- **Proposed resolution**: Keep progress statusline and progress install-statusline, but make first-time settings installation an explicit user action documented in docs/progress-reporting.md; if a SessionStart hook remains, limit it to refreshing an already larch-owned statusLine and launcher



### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/_progress_report_live.py:215-239
- **Concern**: Strict statusline discovery must filter live candidates before mtime ranking. Scenario: Plan text treats liveness as a post-rank veto on the mtime winner ("stale pointer without live registry produces empty statusline output"). A stale implement pointer with fresher timing-ledger activity but no live bgjob can still outrank a genuinely live design/implement session; statusline then prints nothing even though a live run exists.
- **Proposed resolution**: Implement strict discovery as filter-then-rank: among cwd-matched pointers, keep only candidates with at least one matching bgjob registry row whose child or daemon passes registry liveness and is not expired; rank survivors by existing activity mtime; return none when that live set is empty.



### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:1239-1260
- **Concern**: Compact statusline contract omits implement Ship-PR / Step 8+ phases. Scenario: During `implement-step8-ship` bgjob waits `_render_implement` routes to multi-line `_render_ship_pr` (PHASE, PR, iteration, stall fields). The plan's compact fields cover review rounds and design voters but do not define a 1-2 line mapping for ship-pr state, so implementers may reuse the full renderer or emit blank/wrong labels in the longest post-PR waits.
- **Proposed resolution**: Add an explicit compact branch for `ship-pr-state.sh`: e.g. `implement: Ship-PR <PHASE>` plus optional PR/iteration/stall tokens and elapsed from the latest timing mark, capped at two ANSI-yellow lines and excluding Gantt/`_last_artifact` output.



### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/test_progress_statusline.py
- **Concern**: Planned tests omit mixed stale-plus-live discovery regression. Scenario: `test_progress_statusline.py` covers empty stdin, stale-only pointers, and synthetic live registry cases, but not two same-repo candidates where the higher-mtime pointer is stale and a lower-mtime pointer still has live bgjob evidence. That gap would miss the filter-before-rank bug above.
- **Proposed resolution**: Add a test with two cwd-matched pointers: stale high-activity implement tmpdir without registry liveness plus live lower-activity design/implement tmpdir with a live registry row; assert statusline renders the live run, not empty stdout.



### FINDING_21:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/test_progress_statusline.py
- **Concern**: Planned statusline unit test uses forbidden flat Python test path. Scenario: `make py-lint` runs `python/cli.py lint flat-tests` and rejects `python/test_*.py` at repo root except `test_support.py`, so the plan's own validation fails before the feature can ship
- **Proposed resolution**: Move the test to `python/tests/report/test_progress_statusline.py` and update the pytest command in the testing strategy



### FINDING_22:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:496-510
- **Concern**: New Makefile-only statusline harness is not added to agent-lint exclusions. Scenario: The plan adds `scripts/test-sessionstart-statusline.sh` and wires it only through Makefile; agent-lint G004 does not follow Makefile targets, matching the existing SessionStart harness comments, so `lint-only` can fail on the new harness
- **Proposed resolution**: Add an `agent-lint.toml` exclusion and comment for `scripts/test-sessionstart-statusline.sh` next to the other SessionStart harness exclusions



### FINDING_23:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/residual-bash-paths.txt:3-29
- **Concern**: New residual Bash scripts are missing from the residual Bash manifest. Scenario: The plan adds a Bash SessionStart hook and shell harness, but the manifest drives bash-targeting linters and CI shellcheck; omitting the new paths leaves the new runtime hook outside the required residual Bash validation surface
- **Proposed resolution**: Add `scripts/sessionstart-statusline.sh` and `scripts/test-sessionstart-statusline.sh` to `scripts/residual-bash-paths.txt`; if the optional PostToolUse hook lands, add its hook and test scripts too



### FINDING_24:
- **Reviewer(s)**: Cursor-dyn-Statusline Security
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/report/statusline_install.py
- **Concern**: Planned settings.json write lacks symlink refusal parity with launcher. Scenario: Plan mandates larch_io.atomic_write(nofollow=True) only for ~/.cache/larch/statusline.sh; ~/.claude/settings.json gets create-parent plus JSON merge with no nofollow atomic replace and no ancestor symlink walk. Same-UID ~/.claude/settings.json or ~/.claude symlink can redirect the write (python/larch/io.py:266-267 raises only when dest itself is a symlink; mkdir still runs first).
- **Proposed resolution**: session_env already uses _assert_no_symlink_path_or_ancestors before home-cache writes (python/larch/state/session_env.py:951-959, 905-906). Require the same for settings.json and launcher parents: reject symlinked path or ancestor, require regular non-symlink file for reads, write via atomic_write(nofollow=True), fail-open exit 0 with no stdout/stderr.



### FINDING_25:
- **Reviewer(s)**: Cursor-dyn-Statusline Security
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/statusline_install.py
- **Concern**: Larch-owned detection can still clobber a custom statusLine. Scenario: Plan says install when absent or larch-owned and never touch custom lines, but ownership is only Prefer a command path under ~/.cache/larch/ plus a larch marker. A user script at ~/.cache/larch/custom-status.sh matches the directory prefix and can be refreshed/overwritten on SessionStart even though it is not larch-owned.
- **Proposed resolution**: Define larch-owned as exact realpath equality with the canonical ~/.cache/larch/statusline.sh command after normalizing $HOME, or a dedicated marker string embedded only in the installed launcher. Any other statusLine.command leaves the file byte-unchanged.



### FINDING_26:
- **Reviewer(s)**: Cursor-dyn-Statusline Security
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: SECURITY.md
- **Concern**: Planned SECURITY.md note will understate installer write residual risk. Scenario: UPDATED SECURITY.md bullets list files, no-clobber, and fail-open cases but omit symlink/ancestor refusal for settings.json, the same-UID trust model used elsewhere (cf. ship-pr-state.sh at SECURITY.md:122), and that statusline UI output can still show local run metadata (PR URLs, step labels) read from session artifacts.
- **Proposed resolution**: Doc must mirror ship-pr-state symlink refusal language for both statusline.sh and settings.json, state same-UID symlink swap residual risk, cross-link settings precedence from docs/configuration-and-permissions.md, and note statusline reads only local pointers/tmpdir artifacts with empty output on error.



### FINDING_27:
- **Reviewer(s)**: Cursor-dyn-Statusline Security
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/report/statusline_install.py
- **Concern**: Installer failure can emit absolute paths despite fail-silent contract. Scenario: statusline_main gets a broad try/except; install_statusline_main only promises no stdout on success or expected no-op. Uncaught OSError from atomic_write includes refusing to write through symlink: {dest} (python/larch/io.py:267), and cli.py _run_subcommand re-raises non-RuntimeError exceptions (python/larch/cli.py:869-878), producing tracebacks with plugin-root and home paths before SessionStart stderr suppression.
- **Proposed resolution**: Wrap install_statusline_main in except Exception returning 0 with no output; never log or print path-bearing errors. Add a unit test that symlinked settings.json produces empty stdout and does not mutate the target.



### FINDING_28:
- **Reviewer(s)**: Cursor-dyn-Statusline Security
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/cli.py
- **Concern**: progress statusline missing from _MACHINE_STDOUT_KEYS. Scenario: Plan registers progress statusline but does not add it to _MACHINE_STDOUT_KEYS (python/larch/cli.py:649-914). If IMPLEMENT_TMPDIR or DESIGN_TMPDIR is present in the Claude child env, logging_util.quiet_init can redirect FD 1 to a quiet log and the statusline shows blank even when a live run exists.
- **Proposed resolution**: Add ("progress", "statusline") to _MACHINE_STDOUT_KEYS; forbid quiet_init inside statusline_main.



### FINDING_29:
- **Reviewer(s)**: Codex-dyn-Statusline Security
- **Severity**: major
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:76-91,217-225
- **Concern**: The installer only adds `nofollow=True` on the leaf write, but it never rejects symlinked ancestors for `~/.cache/larch/statusline.sh` or `~/.claude/settings.json`. A symlinked parent can redirect the SessionStart write to an arbitrary target, which can defeat the custom `statusLine` no-clobber guarantee and clobber the wrong file.. Scenario: A redirected `~/.cache/larch` or `~/.claude` makes the automated SessionStart write follow the attacker-controlled path instead of the intended launcher or user settings file, so the feature can overwrite the wrong file and the SECURITY.md residual-risk note would understate that exposure.
- **Proposed resolution**: Add the existing ancestor-symlink guard before creating or writing either path, fail open on any symlinked parent, and keep SECURITY.md aligned by saying the installer only touches regular non-symlink files.



