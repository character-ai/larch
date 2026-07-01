## Goal
Implement issue #5925: [IMPLEMENTING] [BUG] hook-bg-poll-guard.sh: cross-session false-positive denial blocks unrelated /implement runs.

## Implementation Plan
## Summary

`scripts/hook-bg-poll-guard.sh`'s generic probe-target check, `bash_has_probe_target()`, matches a candidate Bash command against the literal, unexpanded substrings `$DESIGN_TMPDIR` / `$IMPLEMENT_TMPDIR` / `$SESSION_TMPDIR` regardless of which live `.bg-wait-active` marker directory is being evaluated in the surrounding loop. Because virtually every post-Step-0 `/implement` and `/design` Bash fence conventionally references `"$IMPLEMENT_TMPDIR"` or `"$DESIGN_TMPDIR"` literally, any unrelated, genuinely-live background-wait marker anywhere under `~/.cache/larch/sessions/*` (e.g. a concurrent `/design` session in a different repo clone) causes the hook to misidentify and deny commands in a completely unrelated `/implement` session, blocking forward progress (observed: Step 18 finalize could not run after a successful merge).

## Original report

Filed via `/implement --merge 5881` in repo clone `larch4` (branch `main`, HEAD `41114e408` at investigation time). During Step 18 (final cleanup/teardown), the orchestrator's finalize command was denied by `hook-bg-poll-guard.sh` with reason `"An immediate-background wait is active. End the turn and wait for <task-notification>; do not poll progress artifacts."`, even though:

- The run's own Step 8 ship-driver had already completed successfully (PR #5920 merged, confirmed via its JSON handoff: `outcome: OK`, `merge_result: admin_merged`).
- Steps 16-17 (rejected findings, final report) had already run and printed the final summary.
- A retry with `run_in_background: true` was denied identically.
- Even the officially-sanctioned Step 8 recovery probe shape (`IMPLEMENT_TMPDIR=<abs>; test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"`) was denied, despite that exact sentinel file being present on disk.

Investigation (see Evidence) traced this to unrelated, concurrently-running `/design` sessions in other repo clones (`larch5`, `larch6`) whose live markers caused the generic deny path to fire for this session's commands.

## Reproduction scenario

1. Start a `/design` session in one larch repo clone (e.g. `larch5`) and let it reach a Step 3 review background wait (writes `~<TMPDIR><id>/.bg-wait-active` with `STEP=design-step3-review`, `TIMEOUT_S=21600`).
2. In a **different** larch repo clone (e.g. `larch4`), run `/implement --merge <issue>` to completion through Step 17.
3. While the `larch5` session's marker is still within its 6-hour timeout window (i.e. genuinely "live"), attempt any Step 18 Bash fence in the `larch4` `/implement` session that references `"$IMPLEMENT_TMPDIR"` and contains a probe-verb-like token (including `python`, since `python3?` in `_PROBE_VERB_RE` also matches bare `python`).
4. Observe the command denied with the generic "An immediate-background wait is active" reason, even though the `larch4` session's own Step 8 marker had already completed and the two sessions share no tmpdir, repo, or process.

## Expected behavior

The hook should only deny a Bash/Read/Monitor/TaskOutput call when it actually targets (or plausibly targets) the **specific** live marker directory being evaluated — not merely because the command contains the generic, unexpanded variable name `$IMPLEMENT_TMPDIR`/`$DESIGN_TMPDIR` that happens to also appear in commands belonging to a completely unrelated, concurrently-running session.

## Observed behavior

Every `/implement` Step 18 Bash fence in the affected session was denied, including the documented sanctioned recovery probe, because a probe-verb match (`test`, `python`, etc.) plus a probe-target match (bare literal `"$IMPLEMENT_TMPDIR"` text) fired against live markers belonging to entirely different, unrelated sessions (`claude-design-larch5-kjf35dgq`, `claude-design-larch6-_8s9eb1b`). The run's actual substantive work (PR #5920 for issue #5881) had already completed and merged; only the final teardown/cleanup step was blocked. The GitHub tracking issue was already `CLOSED`/`COMPLETED` from an earlier automated step, but its title stayed at the `[IMPLEMENTING]` prefix because the terminal rename lives in the blocked Step 18b.

## Root cause analysis

In `scripts/hook-bg-poll-guard.sh`, `bash_has_probe_target()` (function definition around line 604) is:

```bash
bash_has_probe_target() {
  local cmd="$1" dir="$2" cwd_canon="$3"
  local design_tmpdir_ref="\$DESIGN_TMPDIR"
  local design_tmpdir_braced="\${DESIGN_TMPDIR}"
  local session_tmpdir_ref="\$SESSION_TMPDIR"
  local session_tmpdir_braced="\${SESSION_TMPDIR}"
  local implement_tmpdir_ref="\$IMPLEMENT_TMPDIR"
  local implement_tmpdir_braced="\${IMPLEMENT_TMPDIR}"
  case "$cmd" in
    *"$design_tmpdir_ref"*|*"$design_tmpdir_braced"*|*"$session_tmpdir_ref"*|*"$session_tmpdir_braced"*|*"$implement_tmpdir_ref"*|*"$implement_tmpdir_braced"*|*"$dir"*|*tasks/*.output*) return 0 ;;
  esac
  ...
```

The first six alternatives in the `case` statement match the bare, unexpanded variable-name text and do **not** depend on `dir` (the specific live marker directory currently being checked in the caller's loop over all live markers). Only the seventh alternative, `*"$dir"*`, is actually scoped to the current marker. Since this function is called once per live marker directory inside the deny loop (around lines 720-743, e.g. `bash_has_probe_verb "$cmd" && bash_has_probe_target "$cmd" "$dir" "$cwd_canon"`), and `marker_candidates()` (around line 48) scans **all** sessions under `~/.cache/larch/sessions/*` — not just the current one — a live marker belonging to any unrelated session is enough to make `bash_has_probe_target` return true for any command that merely mentions the generic tmpdir variable name, which is the documented, conventional way every `/implement`/`/design` Bash fence is written.

`bash_has_probe_verb()` (using `_PROBE_VERB_RE` around line 471, `'(ls|cat|wc|stat|find|head|tail|test|grep|rg|ripgrep|awk|sed|python3?|jq|dd|cmp)'`) is satisfied by nearly every real orchestrator command too, since `python3?` also matches bare `python` (e.g. `python/cli.py`), and most fences also contain `test`, `cat`, etc. somewhere in the launcher chain.

The step-specific probes (`bash_is_terminal_sentinel_foreground_probe`, `bash_is_step8_handoff_foreground_probe`) are correctly scoped to the current session's own live marker via `probe_target_live_dir(...)`/`probe_target_live_dir_step8(...)`, so they don't have this bug — but once a session's own marker has completed, its commands no longer match those specific-probe functions and fall through to the generic per-live-dir loop, where the cross-session false positive applies.

Confidence: high. Traced with the actual denial messages in this session, confirmed by direct inspection of `~/.cache/larch/sessions/*/.bg-wait-active` contents (marker STEP, PID, START_EPOCH, TIMEOUT_S) showing two markers from unrelated repo clones within their live window at the time of the denials.

## Evidence

- `scripts/hook-bg-poll-guard.sh` line 48: `marker_candidates()` scans `$HOME/.cache/larch/sessions` (maxdepth 2) and `${TMPDIR:-/tmp}` (maxdepth 3) for `.bg-wait-active`, with no session/repo scoping.
- `scripts/hook-bg-poll-guard.sh` line 471: `_PROBE_VERB_RE='(ls|cat|wc|stat|find|head|tail|test|grep|rg|ripgrep|awk|sed|python3?|jq|dd|cmp)'` — `python3?` matches bare `python`.
- `scripts/hook-bg-poll-guard.sh` line 604 (`bash_has_probe_target`) and its call sites at lines 727, 730, 733, 736, 739, 742, 745 — each call is inside a `while IFS= read -r dir` loop over every live marker directory, and the first six `case` alternatives ignore `$dir` entirely.
- Live session inspection (this run, 2026-07-01, epoch ~1782889839): `find ~/.cache/larch/sessions -maxdepth 2 -name .bg-wait-active` returned 10 markers, all named `claude-design-*` — none matching this session's own tmpdir (`claude-implement-larch4-65gvuelx`). Ages: 8 markers were ~11.6-12.4 days old (`START_EPOCH` far beyond `TIMEOUT_S=21600` + 60s grace, correctly stale); 2 markers (`claude-design-larch5-kjf35dgq`, `claude-design-larch6-_8s9eb1b`) had `START_EPOCH` roughly 59 and 79 minutes before the check, i.e. genuinely within their live window.
- This session's own `implement-step8-ship` marker/sentinel (`$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc`) was present and correctly recognized as complete — the denial was not caused by this session's own marker.
- Denial reason string observed verbatim: `"An immediate-background wait is active. End the turn and wait for <task-notification>; do not poll progress artifacts."` (matches `json_deny()` around line 407-412).
- **Distinct from prior `hook-bg-poll-guard.sh` fixes** (checked via `/issue` dedup Phase 2, full bodies read): #4450 (missing `marker_step_completed` cases for `design-step5c`/`design-step-final-summary`, fixed), #4661 (a *different* hook, `hook-progress-report.sh`, selecting the wrong tmpdir by mtime, fixed), #4688 (premature-notification liveness left the guard live with no sanctioned foreground recovery probe, fixed by adding the terminal-sentinel probe whitelist), #5684 (CLAUDE_PID-based session scoping never matched in production, so the hook did nothing at all; fixed by removing PID scoping and relying on `kill -0` + age), #5868 (the `marker_candidates()` TMPDIR `find` scan timing out under load on macOS due to scanning the entire shared per-user TMPDIR; closed 2026-07-01, same day as this report). None of these touch `bash_has_probe_target()`'s per-live-dir matching logic — the mechanism reported here would still reproduce even with #5868's narrower/faster scan, since a faster scan still surfaces the same unrelated live markers, and #5684's removal of (non-functional) PID scoping never provided cross-session isolation for the generic literal-variable-name branches in the first place.

## Affected files

- `scripts/hook-bg-poll-guard.sh` — `bash_has_probe_target()` (~line 604) is the primary defect site; `marker_candidates()` (~line 48) is the unscoped-scan contributor; `_PROBE_VERB_RE` (~line 471) broadens the probe-verb match to ordinary orchestrator commands.
- `skills/shared/orchestrator-never.md` and `skills/implement/SKILL.md` NEVER #8 — document the intended guard behavior and the sanctioned Step 8 recovery probe; may need a note about this cross-session failure mode and/or a documented manual-unstick path once fixed.

## Suggested fix(es)

- Scope the generic `$DESIGN_TMPDIR`/`$IMPLEMENT_TMPDIR`/`$SESSION_TMPDIR` literal-text branches in `bash_has_probe_target()` to only count when there is some actual evidence the command targets *this* `dir` — for example, only accept the bare-variable-name match when `cwd_canon` equals `dir` (the command is running with that session's directory as cwd), or when the command also contains `dir`'s literal path, rather than treating the mere presence of the generic variable name as a match against every live marker in the system.
- Alternatively (or additionally), scope `marker_candidates()` / the live-marker scan to the current tool call's `cwd` or an equivalent session-identifying signal, so an unrelated repo clone's live marker never enters the deny loop for this session's commands at all.
- Consider whether `_PROBE_VERB_RE`'s `python3?` alternative is too broad given `python/cli.py` is the primary way this repo's own orchestration scripts are invoked; a stricter match (e.g. requiring `python3` or `python -c`/`python -m` shapes rather than bare `python`) may reduce false-positive probe-verb matches without weakening the guard's actual intent (catching ad hoc `python3 -c "..."` polling one-liners).
- Add a regression test alongside the existing `scripts/test-hook-no-progress-guard.sh` / bg-poll-guard test coverage that exercises two distinct session tmpdirs, one with a genuinely live marker and one without, and asserts that a command in the marker-free session is allowed.

## Open questions

- Should the fix also address proactive cleanup of long-abandoned `.bg-wait-active` markers (the 8 markers found here were 11.6-12.4 days old), or is relying on the `TIMEOUT_S` + `kill -0` fallback during the next hook invocation considered sufficient, given they were correctly excluded here?
- Is there a supported manual "unstick" path today (e.g. an env var or explicit marker removal) that operators should be pointed to when this cross-session collision occurs, until the underlying scoping bug is fixed?

## Test plan
(no test plan section in plan-file)
