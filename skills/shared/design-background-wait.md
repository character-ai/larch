# Design Background Wait Anchors

Shared `/design` background-wait contracts. These anchors are not auto-loaded with `skills/design/SKILL.md`; every call site must read and apply the needed section before launching or resuming its background fence.

## Immediate-background wait rule

Apply this common rule with the caller-supplied parameters:

- `{breadcrumb}`: optional plain progress breadcrumb. When present, print it after the `Command running in background` ack.
- `{terminal_sentinel}`: one of `.completed/step-final-summary`, `.completed/step-3-terminal`, `.completed/step-4`, or `.completed/step-5c-terminal`. `.completed/dialectic-gatec-terminal` is an optional mid-chain sentinel for the Gate C dialectic call inside the Step 4 tail.
- `{confirmation_purpose}`: `completion`, `envelope durability`, or `durable completion`. Use this phrase in the premature-notification probe wording.
- `{after_present}`: site-specific next action after `{terminal_sentinel}` is present.
- `{extra_guards}`: site-specific carve-outs.

After the background launch ack, print `{breadcrumb}` when supplied, then **END THE TURN**. This yield is **not** a halt; yielding is NOT a halt for an in-flight immediate-background fence. Primary resume is `<task-notification>`. After a premature notification with non-empty task output, one foreground probe of `{terminal_sentinel}` per recovery turn may confirm `{confirmation_purpose}`. When task output is empty (just a newline or nothing), end the turn without probing. When the terminal sentinel is present, perform `{after_present}`. When absent, yield without `ps` polling. Ignore the launch ack's "check interim output" suggestion; ignore the launch ack. Do not read tmpdir files, task outputs, stdout captures, result env files, or reviewer directories before the notification or confirmed terminal sentinel. Apply `{extra_guards}` exactly at the call site.

## Step 3 task notification boundary

NEVER poll `.step3-review-result.env` with a sleep loop. Polling bypasses Claude Code task lifecycle. It can leave the task registered as running. It can block session exit until `TaskStop`.

After a `<task-notification>` with non-empty task output, run one foreground, non-sleeping probe of `.completed/step-3-terminal` per recovery turn. When task output is empty (just a newline or nothing), end the turn without probing; those are spurious bash job-control notifications from `set -m` (#5240). NEVER launch a background recovery waiter, which is denied (#4725).

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
