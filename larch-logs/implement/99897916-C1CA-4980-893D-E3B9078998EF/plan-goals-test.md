## Goal
Implement issue #5478: [IMPLEMENTING] [BUG] Orchestrator probes step-3-terminal sentinel on every spurious task-notification even when output is empty.

## Implementation Plan
## Summary

During a `/design` Step 3 plan-review wait, the orchestrator ran the foreground terminal-sentinel probe (`[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ] && echo DONE || echo WAIT`) on every spurious `<task-notification>` turn, including turns where the task output was empty. This burned O(N) turns and tokens while waiting for reviewers, even though the rule says "when task output is empty, end the turn without probing."

## Original report

The operator interrupted a `/design 5468` run after observing roughly 12 consecutive turns where the orchestrator probed the sentinel on every spurious `<task-notification>`, each turn burning one Bash tool call and one model generation. The task output file contained only a single newline on every notification turn.

## Reproduction scenario

1. Start `/design <issue>` where the plan-review panel takes several minutes (normal).
2. The review script runs as an immediate-background Bash task.
3. The bash job-control `set -m` in the review wrapper emits spurious `<task-notification>` events with empty stdout (documented as #5240).
4. On each empty notification, the orchestrator should end the turn without probing. Instead it ran `[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ] && echo DONE || echo WAIT` on every turn regardless of whether the output was empty.
5. Result: N probe-turns fired before the real completion notification, proportional to however many spurious notifications the shell job-control layer emitted.

## Expected behavior

When `<task-notification>` fires with empty task output (just a newline or nothing): end the turn with no Bash tool call. The SKILL.md rule and `skills/shared/design-background-wait.md` both state this explicitly. The next real completion notification delivers non-empty content and triggers exactly one probe.

## Observed behavior

The orchestrator probed the terminal sentinel on every notification turn regardless of task-output content. Observed sequence:

- Notification 1: task output empty → probe → WAIT → end turn (first probe correct if output had content; was wrong here)
- Notification 2: PostToolUse Read hook read task output file, warned "poll detected" → probe → WAIT
- Notifications 3–12: model skipped reading the task output file entirely and went straight to the sentinel probe → WAIT → end turn, repeat

The PostToolUse Read hook went silent after the second read (because the model stopped reading the task output file), while the sentinel probes continued undetected.

## Root cause analysis

**Primary (prompt-level):** The orchestrator did not check whether the task output was empty before deciding to probe. The empty-output check is purely prompt-enforced; no hook enforces it. Each new `<task-notification>` triggered a Bash probe turn regardless of content.

**Why existing machinery did not stop it:**

1. `scripts/hook-bg-poll-guard.sh` line 441: `bash_is_terminal_sentinel_foreground_probe "$cmd" && exit 0` — the hook explicitly allows the foreground `[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ] && echo DONE || echo WAIT` form and exits 0 (allow). This is correct for the valid single-probe case. But the hook sees only the Bash command, not the notification-output context. It cannot distinguish a probe triggered by an empty-output notification from one triggered by a non-empty notification. There is no per-session probe counter or empty-output state in the hook.

2. PostToolUse Read hook (task-output poll detection): fires only when the model Reads the task output file. After the second read triggered the "poll detected" warning, the model stopped reading the output file and went straight to Bash sentinel probes. The Read hook went silent while the burn continued undetected via Bash.

3. `skills/shared/design-background-wait.md` rule is prompt-enforced only. No structural enforcement exists.

4. The #5418 fingerprint rule (skip probe when notification content is byte-identical to the previous non-empty notification) does not apply here because every notification had empty content, not repeated non-empty content.

## Evidence

- `skills/shared/design-background-wait.md` line 15: "When task output is empty (just a newline or nothing), end the turn without probing."
- `skills/shared/design-background-wait.md` line 21: same rule restated for Step 3.
- `scripts/hook-bg-poll-guard.sh` line 441: unconditional allow for `bash_is_terminal_sentinel_foreground_probe` — hook has no empty-output awareness.
- PostToolUse Read hook fires on Read tool only; Bash tool sentinel probes bypass it.
- Task output file showed 1 line (empty) on every notification turn; model confirmed this on the second read (PostToolUse hook warned) then stopped reading.

## Affected files

- `skills/design/SKILL.md` — Anti-pattern #4 and Step 3 post-notification sequence define the probe rule; wording does not prevent prompt-level non-compliance.
- `skills/shared/design-background-wait.md` — Step 3 task notification boundary rule; prompt-enforced only.
- `scripts/hook-bg-poll-guard.sh` — allows foreground sentinel probes unconditionally; no empty-output context awareness.

## Suggested fix(es)

**Option A — Hook-level enforcement (mechanical, preferred):** Extend `hook-bg-poll-guard.sh` to track a "consecutive foreground-probe WAIT count" per live design-tmpdir in a counter file (e.g. `$DESIGN_TMPDIR/bg-poll-guard-probe-denials.count`). After N consecutive foreground probe attempts (e.g. N=2) on the same sentinel without the sentinel becoming present, deny further probes until the sentinel appears. This catches the empty-output-notification loop pattern mechanically regardless of whether the model checked the output file.

**Option B — Wording clarification in design-background-wait.md:** Add an explicit tie between "empty output → no probe" and "after getting WAIT from a probe that was on an empty-output turn, do not probe again until a notification with non-empty output arrives." Current wording says end the turn without probing on empty output but does not say what to do if the model already probed and got WAIT before it noticed the output was empty.

**Option C — Hook reads the task output file before allowing the probe:** When the hook detects a foreground terminal-sentinel probe Bash call, it could read the task output file path (resolvable from the live `bg-wait-active` marker) and deny the probe when the output file is empty (≤1 byte). This requires the hook to know the task output file path, which may not be reliably accessible from the hook's INPUT context.

Option A is the safest mechanical fix. It requires only a counter write in the hook and does not need the model to correctly classify the notification output.

## Open questions

- Should the probe-denial counter reset when the sentinel becomes present (or when the background task completes), so it doesn't permanently block future design runs using the same tmpdir?
- Is the PostToolUse Read hook the right place to also detect "Bash tool probe without prior task-output Read in the same turn" as a secondary signal?

## Test plan
(no test plan section in plan-file)
