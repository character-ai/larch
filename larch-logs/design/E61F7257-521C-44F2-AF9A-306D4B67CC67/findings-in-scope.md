### FINDING_1: Flat-tests-compatible test location
- **Reviewer(s)**: Cursor-Arch, Codex-Requirements
- **Severity**: major
- **Concern**: The planned unit test path at the repo root will be rejected by flat-tests lint before the feature can ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Place tests at `python/tests/report/test_progress_statusline.py` (or extend `python/tests/report/test_progress_report.py`) and update the Testing strategy command accordingly
  - From Codex-Requirements: Move the test to `python/tests/report/test_progress_statusline.py` and update the pytest command in the testing strategy

### FINDING_2: Compact statusline needs dedicated ship-pr/design rendering
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The compact statusline path is not explicitly separated from the full report renderers, so ship-pr and design plan-review waits can fall back to coarse timing marks or path-heavy artifact output instead of the intended 1–2 line summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a compact ship-pr branch: when `ship-pr-state.sh` exists for the strict-live candidate, surface `PHASE` (and stall/PR fields when set) on line 1 instead of only the latest timing mark
  - From Cursor-Arch: Define a statusline-only compact formatter (1–2 lines, yellow ANSI) that never calls `_last_artifact` or the full multi-section renderers; add a test that corrupt or stale ledgers cannot emit path fragments
  - From Cursor-Innovation: Mirror _render_implement/_render_design routing in a dedicated compact helper: when ship-pr-state.sh exists emit a one-line ship-pr summary; when design plan-review is active emit round/reviewer counts without Gantt sections
  - From Cursor-Innovation: Explicitly forbid _last_artifact and multi-section Gantt helpers in statusline_main; cap output to skill step elapsed plus optional round/reviewer or voter counts
  - From Cursor-Pragmatic: Mirror `_render_implement` routing in the compact path: when `ship-pr-state.sh` exists emit a one-line ship phase summary (phase, optional PR/iteration); keep review-round fields only on the Step 5 branch
  - From Cursor-Requirements: Add an explicit compact branch for `ship-pr-state.sh`: e.g. `implement: Ship-PR <PHASE>` plus optional PR/iteration/stall tokens and elapsed from the latest timing mark, capped at two ANSI-yellow lines and excluding Gantt/`_last_artifact` output.

### FINDING_3: Read-only live discovery
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Liveness discovery should be read-only; mutating registry entries during render can reap rows needed by background waits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document and implement strict discovery as read-only: scan `registry.iter_entries()`, match resolved `entry.tmpdir`, treat live when `child_liveness` or `daemon_liveness` is true and entry is not expired; never unlink or mutate registry during render

### FINDING_4: StatusLine ownership/composition must be exact and non-destructive
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-dyn-Statusline Security
- **Severity**: major
- **Concern**: The installer's notion of a larch-owned or refreshable statusLine is too loose and too narrowly scoped, so a custom or higher-precedence statusLine can be clobbered or keep shadowing the launcher.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin ownership: expanded `statusLine.command` equals `~/.cache/larch/statusline.sh` (or the configured cache launcher path); only that path may be installed/refreshed; all other commands are immutable
  - From Codex-Innovation: Detect the winning settings layer and either install there when larch-owned or provide a non-destructive composition path for an existing `statusLine` command
  - From Cursor-dyn-Statusline Security: Define larch-owned as exact realpath equality with the canonical `~/.cache/larch/statusline.sh` command after normalizing $HOME, or a dedicated marker string embedded only in the installed launcher. Any other statusLine.command leaves the file byte-unchanged.

### FINDING_5: Filter live candidates before mtime ranking
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: Candidate selection still ranks by stale mtime, so a live run can be hidden behind a stale pointer and the progress surface can show the wrong session or return empty output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: When any same-cwd candidate has live bgjob evidence prefer those candidates before mtime ranking for both strict statusline and progress report; keep the stale note only for the selected pointer when it lacks registry proof
  - From Cursor-Requirements: Implement strict discovery as filter-then-rank: among cwd-matched pointers, keep only candidates with at least one matching bgjob registry row whose child or daemon passes registry liveness and is not expired; rank survivors by existing activity mtime; return none when that live set is empty.
  - From Cursor-Requirements: Add a test with two cwd-matched pointers: stale high-activity implement tmpdir without registry liveness plus live lower-activity design/implement tmpdir with a live registry row; assert statusline renders the live run, not empty stdout.

### FINDING_6: Statusline installer JSON contract
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The exact shape of the statusLine JSON written to settings is underspecified, so Claude Code may ignore or mis-parse it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin the exact statusLine object written (match repo probe: type command command refreshInterval) and test round-trip parse in test_progress_statusline.py

### FINDING_7: SECURITY.md needs installer-specific and symlink-risk coverage
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-Statusline Security
- **Severity**: major
- **Concern**: The security documentation for the new SessionStart installer under-describes the write surface and residual symlink/trust risks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add a SessionStart statusline installer paragraph listing files written (~/.cache/larch/statusline.sh and user settings.json statusLine only when absent or larch-owned) no-clobber rules and hook ordinal relative to existing SessionStart hooks
  - From Cursor-dyn-Statusline Security: Doc must mirror ship-pr-state symlink refusal language for both statusline.sh and settings.json, state same-UID symlink swap residual risk, cross-link settings precedence from docs/configuration-and-permissions.md, and note statusline reads only local pointers/tmpdir artifacts with empty output on error.

### FINDING_8: Install failures must stay fail-silent
- **Reviewer(s)**: Cursor-Pragmatic, Codex-dyn-Statusline Security
- **Severity**: major
- **Concern**: The installer's error path can emit stderr tracebacks and absolute paths, breaking the fail-silent contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `2>/dev/null` to `~/.cache/larch/statusline.sh` and require `statusline_main` never write stderr on any path (outer `try/except` returns exit 0 with empty stdout)
  - From Codex-dyn-Statusline Security: Wrap install_statusline_main in except Exception returning 0 with no output; never log or print path-bearing errors. Add a unit test that symlinked settings.json produces empty stdout and does not mutate the target.

### FINDING_9: settings.json writes need atomic replace
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: A mid-write SessionStart interruption could corrupt the user's entire settings.json file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Use `larch_io.atomic_write` (or write-temp-then-rename) for settings.json updates; keep invalid-JSON fail-open before any write

### FINDING_10: bgjob wait matcher is too narrow
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The optional hook's matcher can miss real production wait commands and never emit progress snapshots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: If the optional hook ships, match any Bash command containing `bgjob wait` with `--step` and `--tmpdir`, or normalize through the same launcher pattern skills use today

### FINDING_11: Residual Bash manifest needs new paths
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Concern**: New Bash SessionStart scripts would sit outside the residual Bash validation surface unless the manifest is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add `scripts/sessionstart-statusline.sh` and `scripts/test-sessionstart-statusline.sh` to `scripts/residual-bash-paths.txt`; if the optional PostToolUse hook lands, add its hook and test scripts too

### FINDING_12: New harness needs agent-lint exclusion
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The new statusline harness will be linted unexpectedly if it is wired only through Makefile targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add an `agent-lint.toml` exclusion and comment for `scripts/test-sessionstart-statusline.sh` next to the other SessionStart harness exclusions

### FINDING_13: Symlink refusal must cover ancestors, not just the leaf
- **Reviewer(s)**: Cursor-dyn-Statusline Security, Codex-dyn-Statusline Security
- **Severity**: major
- **Concern**: Leaf-only nofollow protection is insufficient for `~/.cache/larch/statusline.sh` and `~/.claude/settings.json`; a symlinked ancestor can redirect the SessionStart write to the wrong file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Statusline Security: session_env already uses _assert_no_symlink_path_or_ancestors before home-cache writes (python/larch/state/session_env.py:951-959, 905-906). Require the same for settings.json and launcher parents: reject symlinked path or ancestor, require regular non-symlink file for reads, write via atomic_write(nofollow=True), fail-open exit 0 with no stdout/stderr.
  - From Codex-dyn-Statusline Security: Add the existing ancestor-symlink guard before creating or writing either path, fail open on any symlinked parent, and keep SECURITY.md aligned by saying the installer only touches regular non-symlink files.

### FINDING_14: progress statusline must be registered for machine stdout
- **Reviewer(s)**: Codex-dyn-Statusline Security
- **Severity**: minor
- **Concern**: The new `progress statusline` command can be squelched by quiet-init unless it is registered as machine stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Statusline Security: Add ("progress", "statusline") to `_MACHINE_STDOUT_KEYS`; forbid quiet_init inside statusline_main

### FINDING_15:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/report/_progress_report_live.py:215-239
- **Concern**: [SCOPE-REDUCTION] Pointer-glob discovery scales with stale pointer pile. Scenario: Statusline refresh every ~10s globbing all current-*-env-*.sh can scan 1000+ stale files (observed in run logs) before liveness checks
- **Proposed resolution**: For statusline strict discovery scan registry.iter_entries() for live rows whose CLONE_PATH matches cwd then resolve tmpdir/skill; use pointer glob only as fallback when no live registry row exists

### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/report/statusline_install.py:1
- **Concern**: [SCOPE-REDUCTION] First-run SessionStart auto-installs a global statusLine instead of keeping installation opt-in. Scenario: The plan creates or rewrites ~/.claude/settings.json whenever no statusLine exists, so merely starting Claude with the plugin changes user-level UI state for all sessions and deletion is not a durable opt-out because the next SessionStart reinstalls it
- **Proposed resolution**: Keep progress statusline and progress install-statusline, but make first-time settings installation an explicit user action documented in docs/progress-reporting.md; if a SessionStart hook remains, limit it to refreshing an already larch-owned statusLine and launcher
