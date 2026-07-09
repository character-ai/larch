## Goal
Implement issue #6624: [IMPLEMENTING] [BUG] p/progress zero-cost progress reports unreachable during bgjob chunked….

## Implementation Plan
## Plan

## Approach

Implement the converged design from the 2026-07-08 operator-discussion comment on #6624 (it supersedes the body's "Suggested fix(es)" items 1-6): file-based progress breadcrumbs written by every phase, a dumb statusline reader that tails them, zero-config auto-install into the clone's gitignored `.claude/settings.local.json`, and full retirement of the typed `p`/`progress` surface now that its gate #6529 has landed (closed 2026-07-08). Carry over the review-hardened guards from design run E61F7257: shared ancestor-symlink guard, `atomic_write(nofollow=True)`, `_MACHINE_STDOUT_KEYS` registration, and the fail-silent reader contract. Do not weaken the bgjob transport; no progress text may enter tool results or model context.

- Writer: one append-only progress file per clone at `~/.cache/larch/progress/<clone-hash>.log` (hash of the repo-root realpath). Atomic single-line appends; lines self-describe as `[<skill> <step>] <what happened>`.
  - Content rules (operator decisions): every breadcrumb states what happened; bare counters banned (`reviewers 7/12 done`, never `reviewers 7/12`); NO URLs — identify entities by number (`PR #6626`, `issue #6624`, `round 13`); one line, no newlines or tabs, no length cap (~250-char lines verified rendering); reader may truncate to `COLUMNS`.
  - Do not reuse bgjob stdout logs; the progress file is a human contract.
- Tier 1, automatic: piggyback the writer on the timing-ledger mark writer so every numbered step in every skill emits a start breadcrumb with zero per-skill work (`[implement 3] checks started`, `[design 2b] plan drafting started`).
- Tier 2, curated: hand-placed events in the long-phase Python drivers: review-loop rounds (launching N reviewers by vendor, reviewers M/N done, aggregator launched, vote judges launched, voting done X/Y accepted | applying fixes, post-fix checks running) and ship-pr phase transitions (running named checks, creating PR, `PR #NNNN created`, CI running, fixing CI issues round N with failing job names, rebase + merge started, merged).
- Reader: `progress statusline` — dumb and fast (<50ms target). Resolve the per-clone file from statusline stdin JSON (`workspace.current_dir`, falling back to `cwd`), tail the last N lines (default 1, config knob), print all-yellow `larch HH:MM: <latest breadcrumb>`. Minute-resolution time; calm rendering (identical repaint when nothing changed; no per-tick counters). `(stale Nm)` annotation when the file mtime is old and no live bgjob registry row exists; blank well past the threshold. Empty stdout + exit 0 on every no-data or error path.
- Auto-install, zero operator action: larch Step 0 session setup and the SessionStart hook idempotently merge the statusLine block into the clone's gitignored `.claude/settings.local.json` (project-local hot-reloads in ~2s, verified live); `refreshInterval: 2` (timer verified firing every 2s during a 50s foreground Bash call). Stable launcher `~/.cache/larch/statusline.sh` refreshed to the current plugin root. Chain a pre-existing user-scope statusline (run it first, append larch output) because local scope overrides user. Opt-out env var; one-line notice on first install.
- Retirement (gate #6529 landed): remove the UserPromptSubmit hook surface, the `progress report` verb, live-run discovery, the mid-run renderers, their tests, and doc references. Keep `render-phase-detail`, the end-of-run Gantt renderer, and the `write-design-round-meta` / `write-implement-round-meta` verbs; the final summary and run-log flush consume them.

## Files to modify/create

### NEW: python/larch/report/progress_file.py

Writer helper (stdlib-only).

- `progress_path(repo_root) -> Path`: `~/.cache/larch/progress/<sha256[:16] of repo-root realpath>.log`.
- `append_breadcrumb(repo_root, skill, step, text)`: atomic single-line append; strip or reject newlines and tabs; format `[<skill> <step>] <text>`; best-effort (a write failure never fails the caller).
- Age-based cleanup helper for old progress files.
- CLI verb `progress note` for step wrappers and drivers that live outside Python.

### NEW: python/larch/report/statusline.py

Reader.

- `statusline_main(argv)` registered as `progress statusline`; no `quiet_init`; lazy stdlib-only imports; target <50ms.
- Parse statusline stdin JSON defensively; any invalid or non-object input emits nothing and exits 0.
- Resolve the clone from `workspace.current_dir`, falling back to `cwd`; tail last N lines (default 1; env knob, max 3).
- Render `larch HH:MM: <breadcrumb>` wrapped in ANSI yellow; minute-resolution clock and `Nm` elapsed only; identical repaint when state is unchanged.
- Staleness: append `(stale Nm)` when file mtime exceeds the threshold and no live bgjob registry row matches this clone; render nothing when far past it.
- Fail-silent contract: empty stdout and exit 0 for missing, empty, or corrupt files and for any internal exception; never error text, whitespace-only output, or partial rows. Optional truncation to `COLUMNS`.

### NEW: python/larch/report/statusline_install.py

Installer.

- `install_statusline_main(argv)` registered as `progress install-statusline`; `--plugin-root` required or defaulted from `CLAUDE_PLUGIN_ROOT`; `--repo-root` names the target clone; test seams for home/cache roots.
- Honor the opt-out env var (`LARCH_STATUSLINE_DISABLE=1`): do nothing, silently.
- Write the stable launcher `~/.cache/larch/statusline.sh` via `atomic_write(..., nofollow=True, mode=0o755)`: it execs the current plugin's `progress statusline`; when a non-larch USER-scope `statusLine` command exists, run it first and append larch output (local scope overrides user, so chaining preserves it); bound the chained command with a short timeout; fail silent when python3 or cli.py is unavailable.
- Merge into `<repo>/.claude/settings.local.json`: create a minimal object when absent; invalid JSON fails open and is never overwritten; absent `statusLine` installs the larch entry with `refreshInterval: 2`; larch-owned entries refresh; a non-larch LOCAL entry is left unchanged.
- Path safety before every read or write: `larch.io.assert_no_symlink_path_or_ancestors` on the target, regular-file check for existing reads, exit 0 with no output on any refusal.
- One-line notice on first install (Step 0 path only), with a sentinel so it never repeats; no stdout on success or no-op; preserve unrelated settings keys.

### UPDATED: python/larch/io.py

- Add public `assert_no_symlink_path_or_ancestors(path: Path) -> None`, moved from `session_env.py` with identical behavior (raises `OSError` on any symlink in the path or its ancestors).

### UPDATED: python/larch/state/session_env.py

- Replace private `_assert_no_symlink_path_or_ancestors` call sites with the shared `larch.io` helper and remove the private copy.

### UPDATED: python/larch/report/timing.py

- Tier-1 piggyback: the `timing mark` writer also appends a step-start breadcrumb (`[<skill> <step>] <label> started`) through `progress_file.append_breadcrumb`; best-effort and fail-soft so a progress write can never fail a timing mark.

### UPDATED: python/larch/review/round_runner.py

- Tier-2 curated review-loop events: launching N reviewers (by vendor), reviewers M/N done, aggregator launched, vote judges launched, voting done X/Y accepted | applying fixes, post-fix checks running.

### UPDATED: python/larch/review/review_and_fix.py

- Same curated events for the /implement Step 5 loop entry points it owns.

### UPDATED: python/plan_review.py

- Same curated events for the /design Step 3 loop (rounds, launches, votes, apply).

### UPDATED: python/larch/implement/ship.py

- Tier-2 events at each ship-pr PHASE transition the driver already tracks: running relevant checks (named shards), creating PR, `PR #NNNN created`, CI running for `PR #NNNN`, fixing CI issues round N | failing: job names, rebase + merge started, merged.

### UPDATED: python/larch/cli.py

- Add `("progress", "statusline")`, `("progress", "note")`, and `("progress", "install-statusline")`.
- Add `("progress", "statusline")` to `_MACHINE_STDOUT_KEYS`.
- Remove `("progress", "report")`.
- Keep `("progress", "render-phase-detail")` and both `("progress", "write-*-round-meta")` rows unchanged.

### REWRITTEN: python/larch/report/progress_report.py

- Remove `report_main` and the mid-run machinery: `_render_implement`, `_render_design`, `_render_step5`, `_render_design_plan_review`, the in-flight Gantt, `_render_ship_pr`, `_render_generic`, `_last_artifact`, and every consumer of live discovery.
- Keep `render_phase_detail`, the end-of-run Gantt renderer, and `write_design_round_meta_main` / `write_implement_round_meta_main`.

### UPDATED: python/larch/report/_progress_report_live.py

- Delete the file (`_discover_live_run`, `LiveRun`, pointer candidates, activity-mtime ranking) after an import audit confirms only the removed mid-run paths used it.

### UPDATED: python/tests/report/test_progress_report.py

- Delete the mid-run report and discovery tests along with the code; phase-detail coverage stays in `python/tests/report/test_review_phase_detail.py`.

### UPDATED: hooks/hooks.json

- Remove the `UserPromptSubmit` entry for `scripts/hook-progress-report.sh`.
- Add `scripts/sessionstart-statusline.sh` under the existing `SessionStart` matcher with a small timeout.

### UPDATED: scripts/hook-progress-report.sh

- Delete (retired; the statusline replaces the typed-keyword surface).

### UPDATED: scripts/hook-progress-report.md

- Delete.

### UPDATED: scripts/test-hook-progress-report.sh

- Delete, plus any structure-test, lint, and Makefile references to it.

### UPDATED: scripts/test-hook-progress-report.md

- Delete.

### NEW: scripts/sessionstart-statusline.sh

- Thin SessionStart hook wrapper: always exit 0; read no prompt content; resolve the plugin root; call `progress install-statusline` with stdout and stderr suppressed; skip silently when python3 or cli.py is missing.

### NEW: scripts/sessionstart-statusline.md

- Hook contract doc: primary caller `hooks/hooks.json` SessionStart; exact writable paths (`~/.cache/larch/statusline.sh`, `<repo>/.claude/settings.local.json`, `~/.cache/larch/progress/`); strict no-clobber; symlink-ancestor refusal; opt-out env var; no network; harness name and Makefile target.

### UPDATED: python/larch/core/cleanup_skill.py

- Age-based sweep of `~/.cache/larch/progress/*.log` joins the existing /cleanup sweep.

### UPDATED: scripts/cleanup-sessionstart.sh

- Same age-based progress-file sweep on the SessionStart path.

### MAY_UPDATE: python/larch/state/bootstrap.py

- Pointer lifecycle audit: `current-implement-env-*.sh` was introduced for progress discovery (#3877). Retire the bootstrap writer, the `session` write verb, and the /cleanup + SessionStart sweep entries for it only if the consumer audit confirms nothing else reads it (`scripts/hook-bg-poll-guard.sh` and `state/bootstrap.py` reference it today). The design-side `current-design-env-*.sh` symlinks stay: Step 0 session rehydration owns them.

### UPDATED: Makefile

- Add a `test-sessionstart-statusline` phony target to one `test-harnesses-N` shard (one physical line); remove retired `test-hook-progress-report` references.

### NEW: python/tests/report/test_progress_statusline.py

- Writer: path derivation from repo-root realpath; atomic append; newline/tab rejection; breadcrumb format; age-based cleanup.
- Reader: empty stdin, invalid JSON, missing cwd, missing/empty/corrupt file all produce empty stdout and rc 0; live file renders the yellow `larch HH:MM:` line; staleness annotation and far-stale blanking; calm repaint (unchanged state produces byte-identical output); `COLUMNS` truncation; no `quiet_init`; `("progress", "statusline")` present in `_MACHINE_STDOUT_KEYS`.
- Installer: absent settings creates entry + launcher; larch-owned refreshes; non-larch LOCAL entry preserved byte-for-byte; invalid JSON untouched; symlinked file or ancestor exits 0 with no writes; user-scope chaining wrapper content; opt-out env var; unrelated keys preserved.
- Tier hooks: `timing mark` appends a breadcrumb; curated driver events emit through the shared writer (unit-level with fakes); a failing progress write never fails the caller.

### NEW: scripts/test-sessionstart-statusline.sh

- Offline harness: script executable; registered in `hooks/hooks.json`; missing python3 exits 0 with no stdout; missing cli.py exits 0 with no stdout; stub cli receives `progress install-statusline --plugin-root`; silent normal path.

### NEW: scripts/test-sessionstart-statusline.md

- Harness contract doc.

### NEW: docs/progress-reporting.md

- Operator docs: the automatic statusline (what it shows, ~2s cadence verified live during foreground tool calls, calm rendering, staleness annotation, per-clone scope); opt-out env var; chaining with a custom user statusline; the end-of-run full report (`render-phase-detail` Gantt) as the detailed surface; retirement note: the typed `p`/`progress` keyword surface is removed, the statusline replaces it; troubleshooting (invalid `.claude/settings.local.json`, symlinked ancestors, garbled multi-line output falls back to fewer or plainer lines).

### UPDATED: README.md

- Short link to `docs/progress-reporting.md` in the feature reference area.

### UPDATED: docs/installation-and-setup.md

- Auto-install note: larch installs its own statusline per clone with no operator action; opt-out env var; custom statuslines are chained, never clobbered.

### UPDATED: docs/configuration-and-permissions.md

- Settings scopes (local > project > user); exactly what larch writes where (`<repo>/.claude/settings.local.json`, gitignored); no-clobber rule.

### UPDATED: docs/workflow-lifecycle.md

- Live progress visibility now comes from the statusline; `BGJOB_STATUS=WAIT` wait-fence rules unchanged.

### UPDATED: SECURITY.md

- New write surfaces: `<repo>/.claude/settings.local.json` (gitignored, install-if-absent-or-larch-owned only), `~/.cache/larch/statusline.sh`, `~/.cache/larch/progress/*.log`. No-clobber behavior; fail-open on invalid JSON, missing prerequisites, and symlinked targets or ancestors; installer touches only regular non-symlink files whose ancestor chain has no symlinks; reader consumes local files only, makes no network calls, and emits empty output on errors. Remove retired typed `p`/`progress` hook references.

### MAY_UPDATE: AGENTS.md

- Doc sweep: remove typed `p`/`progress` feature references where present; keep references that concern the end-of-run report.

## Edge cases

- Two larch runs in one clone interleave appends in one progress file; breadcrumbs self-identify with `[<skill> <step>]`, so the tail stays readable.
- Multiple clones never cross: files are keyed by repo-root realpath hash, and the reader resolves the clone from statusline stdin.
- A non-larch LOCAL `statusLine` is never modified; a USER-scope statusline keeps rendering via the chaining wrapper.
- Invalid `.claude/settings.local.json` is never overwritten.
- Symlinked launcher, settings, progress paths, or any symlinked ancestor blocks writes silently.
- Breadcrumbs never contain URLs, bare counters, newlines, or tabs; long single lines are allowed; the reader may truncate to `COLUMNS`.
- Stale tails annotate `(stale Nm)`, then blank past the hide threshold; no larch activity renders nothing at all.
- The statusline never prints whitespace-only output or absolute tmpdir paths.
- bgjob wait contracts are unchanged; no progress text enters tool results or model context.

## Failure modes

- Multi-line ANSI output garbles on some terminals: default stays 1 line; fall back to fewer or plainer lines via the documented knob.
- Reader misses its <50ms target through cli.py dispatch: keep imports lazy; if still slow, invoke the reader module directly from the launcher and record the G-CLI-1 deviation inline.
- Retirement breaks an unnoticed consumer of `_discover_live_run` or the implement pointer: run the import and grep consumer audit before each deletion; pointer retirement stays MAY_UPDATE.
- A phase emits no tier-1 mark: tier-2 curated events cover the long phases; short phases still get step-start breadcrumbs from the shared mark writer.
- A chained user statusline command hangs: the wrapper bounds it with a short timeout and still prints the larch line.

## Testing strategy

- `python3 -m pytest python/tests/report/test_progress_statusline.py`
- `bash scripts/test-sessionstart-statusline.sh`
- `bash scripts/test-cleanup-sessionstart.sh`
- `bash scripts/test-sessionstart-health.sh`
- `make py-lint`
- `make py-test` (report, review, and implement modules change)
- `python3 python/cli.py checks run-relevant`

## Difficulty

This is HARD.

The feature half is wide but well-partitioned (writer, reader, installer, curated events in three long-phase drivers); the retirement half deletes a large legacy surface (hook, verb, discovery, renderers, ~3.3k test lines) whose consumers must be audited. Fail-open and fail-silent rules bound the blast radius; the risky edges are settings merging, hook timing, and deleting the old surface cleanly.

difficulty: HARD
diff_added: 1250
diff_deleted: 4400
mechanical_churn: false
oversize_override: operator
diff_lines: 5650

## Acceptance

- A larch skill run in a clean clone auto-installs the statusline (settings.local.json entry + stable launcher) with no operator action; within ~2s a live phase shows a yellow `larch HH:MM: [<skill> <step>] ...` line that keeps updating during foreground bgjob wait fences.
- Non-larch repos and idle clones render nothing; a non-larch LOCAL statusline is never modified; a USER-scope statusline still renders via chaining; `LARCH_STATUSLINE_DISABLE=1` prevents install; the first install prints a one-line notice, once.
- Tier-1 step-start breadcrumbs appear for numbered steps across /design, /implement, and /review, and tier-2 curated events appear for review-loop rounds and ship-pr transitions, all in `~/.cache/larch/progress/<clone-hash>.log`, with no URLs, no bare counters, and single-line entries.
- Calm rendering holds: unchanged state repaints byte-identical text; stale runs annotate `(stale Nm)` and later blank.
- Fail-silent holds: missing, empty, or corrupt progress files, invalid stdin JSON, and internal errors all produce empty stdout and exit 0 — never error text, whitespace, or garbage.
- Retirement is complete: the UserPromptSubmit hook, `progress report` verb, live discovery, mid-run renderers, and their tests are gone; `render-phase-detail`, the Gantt renderer, both round-meta verbs, and the end-of-run report still work; no doc references to the typed keyword surface remain except historical notes.
- Every command in Testing strategy passes.

diff_lines: 5650

## Test plan
(no test plan section in plan-file)
