# Design Background Wait Anchors

Shared `/design` background-wait contracts. These anchors are not auto-loaded with `skills/design/SKILL.md`; every call site must read and apply the needed section before launching or resuming its background fence.

## Immediate-background wait rule

Apply this common rule with the caller-supplied parameters:

- `{breadcrumb}`: optional plain progress breadcrumb. When present, print it after the `Command running in background` ack.
- `{terminal_sentinel}`: one of `.completed/step-final-summary`, `.completed/step-3-terminal`, `.completed/step-4`, or `.completed/step-5c-terminal`. `.completed/dialectic-gatec-terminal` is an optional mid-chain sentinel for the Gate C dialectic call inside the Step 4 tail.
- `{confirmation_purpose}`: `completion`, `envelope durability`, or `durable completion`. Use this phrase in the premature-notification probe wording.
- `{after_present}`: site-specific next action after `{terminal_sentinel}` is present.
- `{extra_guards}`: site-specific carve-outs.

After the background launch ack, print `{breadcrumb}` when supplied, then **END THE TURN**. This yield is **not** a halt; yielding is NOT a halt for an in-flight immediate-background fence. Primary resume is `<task-notification>`. After a premature notification with non-empty task output, one foreground probe of `{terminal_sentinel}` per recovery turn may confirm `{confirmation_purpose}`. When task output is empty (just a newline or nothing), end the turn without probing. After a probe reports the sentinel absent, do not probe again until a notification arrives with new non-empty content; `scripts/hook-bg-poll-guard.sh` denies repeated foreground probes against a still-absent terminal sentinel after a small threshold and clears the clamp once the sentinel appears (#5478). When the terminal sentinel is present, perform `{after_present}`. When absent, yield without `ps` polling. Ignore the launch ack's "check interim output" suggestion; ignore the launch ack. Do not read tmpdir files, task outputs, stdout captures, result env files, or reviewer directories before the notification or confirmed terminal sentinel. Apply `{extra_guards}` exactly at the call site.

Foreground probes are non-sleeping `[ -f … ]` or `test -f …` checks only. Accepted terminal sentinels for probe and completion checks are `.completed/step-3-terminal`, `.completed/step-5c-terminal`, `.completed/step-final-summary`, and `.completed/step-4` for the Step 4 tail path. Do not use `.completed/step-3`, `.completed/step-5c`, or `.step3-review-result.env` as a probe or completion target. The `.step3-review-result.env` ban applies only to probe and completion checks; after `.completed/step-3-terminal` is present, parsing `.step3-review-result.env` for loop routing remains required.

When `$DESIGN_TMPDIR` is not exported, prefix the probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment. When `$DESIGN_TMPDIR` is not exported, prefix the foreground probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment. `WAIT` when absent is expected. When `WAIT` is present, proceed to guarded parsing or call-site handling; do not wait for a second `<task-notification>`. When `WAIT` is absent, yield without polling. This assumes the backgrounded `/design` task reliably re-fires a `<task-notification>` on completion (current evidence indicates it does).

## Step 3 task notification boundary

NEVER poll `.step3-review-result.env` with a sleep loop. Polling bypasses Claude Code task lifecycle. It can leave the task registered as running. It can block session exit until `TaskStop`.

Step 3-specific recovery note: the completion condition MUST be `[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ]`; it MUST NOT be `.step3-review-result.env`.

Foreground terminal-sentinel probe: after a premature notification with non-empty task output, run at most one non-sleeping `[ -f … ]` or `test -f …` probe per recovery turn against `.completed/step-3-terminal`. When task output is empty (just a newline or nothing), end the turn without probing; those are spurious bash job-control notifications from `set -m` (#5240). After a probe returns `WAIT`, do not probe again until a `<task-notification>` arrives with new non-empty content; `scripts/hook-bg-poll-guard.sh` denies repeated foreground probes against a still-absent terminal sentinel after a small threshold and clears the clamp once the sentinel appears (#5478). NEVER launch a background recovery waiter, which is denied (#4725).

Do not launch a background recovery waiter such as `until [ -f … ]; do sleep N; done`: a zero-output background task can fire its own premature notification and amplify into a re-engagement loop, so `scripts/hook-bg-poll-guard.sh` denies it (#4725). Do not use `ps` polling. Do not fall back to Monitor.

If a `<task-notification>` arrives with non-empty content that is byte-identical to the immediately preceding non-empty notification in this wait sequence, yield without probing (#5418) only when `.completed/step-3-terminal` is absent. Track a fingerprint (the first 200 characters) of the last notification content and skip the probe when content matches and the sentinel is not yet written. This prevents turn-burning when the harness re-delivers the same notification while the sentinel is not yet written; when the sentinel is already present, proceed to the post-notification sequence below instead of yielding.

When `.completed/step-3-terminal` is present, run the Step 3 post-notification compact-table sequence and loop-routing parse without waiting for another notification. Route to Step 3b or later only when `.completed/step-3` is also present, because that is the terminal loop-completion milestone. Mid-loop bail-outs may have `step-3-terminal` without `step-3`.

## Step 3 post-notification sequence

After a confirmed `<task-notification>` or terminal-sentinel recovery, execute this authoritative sequence:

1. **Completion gate**: after a confirmed `<task-notification>` or a foreground probe that confirms `$DESIGN_TMPDIR/.completed/step-3-terminal` is present. Do not print before this gate.
2. **Print the compact table once** using this data path:
   - Use the Read tool on `$DESIGN_TMPDIR/reviewer-status-table.txt`.
   - Write the Read result as plain orchestrator chat text.
   - Do not use a Bash tool call, Python script, or any other tool invocation to extract or print the table body; tool output is collapsible.
   - If absent or a symlink (unrefreshable destination), print exactly:
     - `**⚠ Reviewer status table omitted: pre-rendered table not found.**`
3. **Loop routing parse (after the table)**: fully parse `$DESIGN_TMPDIR/.step3-review-result.env` for Step 3 resume / branch routing.

The only Step 3 table output is the verbatim pre-rendered single line from `$DESIGN_TMPDIR/reviewer-status-table.txt`; Python owns icon and elapsed formatting. Print only after confirmed completion via the read-only emit contract. Do not invent in-progress updates, reprint mid-wait, or print a static all-pending table at launch. Do not manually format `📊` reviewer lines in Step 3; Read and emit the file only.

## Step 4 post-notification sequence

For the debate path, the orchestrator backgrounds the whole `design-step3b-tail.sh` fence and uses `.completed/step-4` as the terminal sentinel for durable completion. After confirmed completion, parse rejected-findings markers from the tail stdout, bind `SKIP_APPROVE_REQUESTED_GATEC`, and retain any dialectic digest stdout for Step 4b presentation. Do not re-read `dialectic-clarifier-digest.md` on the same turn when the tail stdout already printed the digest.

## Update Triggers

Update this file when `/design` background wait sentinels, Step 3 result-env routing, reviewer-status table emit rules, or premature-notification recovery contracts change.
