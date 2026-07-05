# Design Background Wait Anchors

Shared `/design` background-wait contracts. These anchors are not auto-loaded with `skills/design/SKILL.md`; call sites must read the needed section before use.

## Immediate-background wait rule

Apply this rule with caller parameters:

- `{breadcrumb}`: optional progress line. Print it after the `Command running in background` ack.
- `{terminal_sentinel}`: one of `.completed/step-final-summary`, `.completed/step-3-terminal`, `.completed/step-4`, or `.completed/step-5c-terminal`. `.completed/dialectic-gatec-terminal` is optional for Gate C inside the Step 4 tail.
- `{confirmation_purpose}`: `completion`, `envelope durability`, or `durable completion`. Use it in premature-notification probe wording.
- `{after_present}`: action after `{terminal_sentinel}` is present.
- `{extra_guards}`: call-site carve-outs.

After the background launch ack, print `{breadcrumb}` when supplied, then **END THE TURN**. This yield is **not** a halt; yielding is NOT a halt for an in-flight fence. Primary resume is `<task-notification>`. After new/changed non-empty premature output, one foreground `{terminal_sentinel}` probe per recovery turn may confirm `{confirmation_purpose}`. Empty output (just a newline or nothing) ends silently: no tool, `wc`, sentinel check, or prose. A prefix-identical repeat (first 200 chars) for the same wait with `{terminal_sentinel}` absent also ends silently. After absent sentinel, probe again only after a new non-empty notification; `scripts/hook-bg-poll-guard.sh` denies repeated foreground probes against a still-absent terminal sentinel after a small threshold and clears the clamp once the sentinel appears (#5478). When present, perform `{after_present}`; when absent, yield without `ps` polling. Ignore the launch ack. Do not read tmpdir files, task outputs, stdout captures, result env files, or reviewer directories before the notification or confirmed terminal sentinel. Apply `{extra_guards}`.

**Universal no-progress circuit breaker (#5639)**: `scripts/hook-no-progress-guard.sh` counts turn ends while a bg-wait marker is live (`Stop` hook) and blocks the next prompt at `LARCH_NO_PROGRESS_GUARD_THRESHOLD` (default 5; `UserPromptSubmit` hook). It auto-disarms when the terminal sentinel appears or the marker is removed. Prose-only "still waiting" turns count.

Foreground probes are non-sleeping `[ -f … ]` or `test -f …` checks only. Accepted probe and completion sentinels are `.completed/step-3-terminal`, `.completed/step-5c-terminal`, `.completed/step-final-summary`, and `.completed/step-4` for the Step 4 tail path. Do not use `.completed/step-3`, `.completed/step-5c`, or `.step3-review-result.env` as probe or completion targets. The `.step3-review-result.env` ban is only for probe and completion checks; after `.completed/step-3-terminal` exists, parse `.step3-review-result.env` for loop routing.

When `$DESIGN_TMPDIR` is not exported, prefix the probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment; for foreground probes: prefix the foreground probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment. `WAIT` when absent is expected. On `DONE`, proceed to guarded parsing or call-site handling; do not wait for a second `<task-notification>`. On `WAIT` or absent sentinel, yield without `ps` polling. This assumes the backgrounded `/design` task reliably re-fires a `<task-notification>` on completion (current evidence indicates it does).

## Step 3 task notification boundary

NEVER poll `.step3-review-result.env` with a sleep loop. Polling bypasses Claude Code task lifecycle, can leave the task registered, and can block exit until `TaskStop`.

Step 3-specific recovery note: the completion condition MUST be `[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ]`; it MUST NOT be `.step3-review-result.env`.

Foreground terminal-sentinel probe: after a premature notification with non-empty task output, run at most one non-sleeping `[ -f … ]` or `test -f …` probe per recovery turn against `.completed/step-3-terminal`. When task output is empty (just a newline or nothing), end the turn without probing; those are spurious bash job-control notifications from `set -m` (#5240). Take no action: call no tool, run no `wc`, run no sentinel check, print no prose. After a probe returns `WAIT`, do not probe again until a `<task-notification>` has new non-empty content; `scripts/hook-bg-poll-guard.sh` denies repeated foreground probes against a still-absent terminal sentinel after a small threshold and clears the clamp once the sentinel appears (#5478). NEVER launch a background recovery waiter, which is denied (#4725).

Do not launch a background recovery waiter such as `until [ -f … ]; do sleep N; done`: a zero-output background task can fire its own premature notification and amplify re-engagement, so `scripts/hook-bg-poll-guard.sh` denies it (#4725). Do not use `ps` polling or Monitor.

If a non-empty `<task-notification>` is prefix-identical to the prior non-empty one in the same wait over the first 200 chars and `.completed/step-3-terminal` is absent, end silently (#5418): no tool call, `ScheduleWakeup`, or prose. The fingerprint is the first 200 chars. If present, run the post-notification sequence. Long reviews may keep `.bg-wait-active`; EXIT clears it and writes the sentinel.

When `.completed/step-3-terminal` exists, run the Step 3 post-notification compact-table sequence and loop-routing parse without waiting for another notification. Route to Step 3b or later only when `.completed/step-3` is also present, the terminal loop-completion milestone. Mid-loop bail-outs may have `step-3-terminal` without `step-3`.

## Step 3 post-notification sequence

After a confirmed `<task-notification>` or terminal-sentinel recovery:

1. **Completion gate**: after a confirmed `<task-notification>` or a foreground probe that confirms `$DESIGN_TMPDIR/.completed/step-3-terminal` is present. Do not print before this gate.
2. **Print the compact table once** using this data path:
   - Use the Read tool on `$DESIGN_TMPDIR/reviewer-status-table.txt`.
   - Write the Read result as plain orchestrator chat text.
   - Do not use Bash, Python, or any tool invocation to extract or print the table body; tool output is collapsible.
   - If absent or a symlink (unrefreshable destination), print exactly:
     - `**⚠ Reviewer status table omitted: pre-rendered table not found.**`
3. **Loop routing parse (after the table)**: parse `$DESIGN_TMPDIR/.step3-review-result.env` fully for Step 3 resume / branch routing.

The only Step 3 table output is the verbatim pre-rendered line from `$DESIGN_TMPDIR/reviewer-status-table.txt`; Python owns icon and elapsed formatting. Print only after confirmed completion via the read-only emit contract. Do not invent in-progress updates, reprint mid-wait, print a static all-pending table, or manually format `📊` reviewer lines.

## Step 4 post-notification sequence

For the debate path, the orchestrator backgrounds the whole `design-step3b-tail.sh` fence. The wrapper arms `.bg-wait-active` with `STEP=design-step4-tail` and uses `.completed/step-4` as the durable-completion sentinel. After completion, parse rejected-findings markers from tail stdout, bind `SKIP_APPROVE_REQUESTED_GATEC`, and retain dialectic digest stdout for Step 4b presentation. Do not re-read `dialectic-clarifier-digest.md` on the same turn when tail stdout already printed it.

## Update Triggers

Update this file when `/design` background wait sentinels, Step 3 result-env routing, reviewer-status table emit rules, or premature-notification recovery contracts change.
