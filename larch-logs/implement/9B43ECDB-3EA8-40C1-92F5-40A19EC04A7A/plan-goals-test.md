## Goal
Implement issue #5701: [IMPLEMENTING] [BUG] Claude plan-review voter intermittently outputs canned acknowledgement instead of casting votes, degrading panel to 2/3 effective judges.

## Implementation Plan
## Summary

The Claude plan-review voter (slot 1, `claude-plan-voter`) intermittently outputs a short conversational acknowledgement instead of reading the ballot file and casting YES/NO votes for each ballot item. When this happens, every ballot item scores `JUDGE_ERROR`, `check_voter_parse_rate` classifies the output as `NOT_SUBSTANTIVE`, the voter is marked failed, and the tally emits "Degraded plan-review panel: 2/3 effective judges produced substantive vote output." The panel then runs at `unanimous-2` tier, lowering acceptance confidence for the entire round.

## Original report

⚠ Degraded plan-review panel: 2/3 effective judges produced substantive vote output.

## Reproduction scenario

The failure occurs non-deterministically during plan-review voting in `/design`. Trigger conditions from committed execution-issues.md records:

1. Run `/design` on any issue.
2. After the review panel completes, observe `DEGRADED_PANEL_WARNING` in the design-step3-review output.
3. Inspect the corresponding `execution-issues.md` warning entry for `voter_tool=claude` with `judge_error_count` equal to `total_findings`.

Confirmed in at least two design run logs (`E14AFC53-76F7-414A-84C2-2847C2AF1014` and `F30AA029-05BD-48F4-9234-2A2A05615BEC`), and the current run (issue #5643, run ID 217EEAF8). The sha256 `fb4cc488c2793f5c1740f7e32565debe31d0f0959842169dcc1cac0eeedcb5a5` appears in multiple runs, indicating Claude outputs the same canned phrase across sessions.

## Expected behavior

The Claude voter reads the ballot file at the path given in the voter prompt, then produces one `FINDING_N: YES/NO` (or `OOS_N: YES/NO`) line for every ballot item. `check_voter_parse_rate` returns `OK`; the voter is counted as an effective judge.

## Observed behavior

The voter output is a conversational acknowledgement, for example:

- `"Ready to review. Please share the plan modifications or findings you'd like me to vote on."`
- `"Understood. I'm ready to review plan modifications as a voting panel member. Please share the items you'd like me to evaluate."`

`judge_error_count` equals `total_findings` (100%). `check_voter_parse_rate` returns `NOT_SUBSTANTIVE`. The voter slot is marked failed. The panel degrades from `full-3` to `unanimous-2`.

## Root cause analysis

Probable cause: when `launch_claude_subprocess_main` launches Claude via `claude --print --output-format json`, the voter prompt instructs Claude to "Read the ballot from this path" (a `Read` tool call) and then cast votes. On some invocations, Claude produces a setup/acknowledgement reply instead of executing the Read call immediately.

This may be because:

- The voter prompt reads as an initial conversational turn that Claude interprets as needing a "proceed" signal from a second turn.
- The `--print` non-interactive mode suppresses retries, so a single unhelpful reply is written to the output file as-is.
- The `parse-rate-retry` path runs `check_voter_parse_rate` with `--retry-prefix-kind plan`, which may retry the launch, but if the retry also produces the canned response (same sha256 seen in two rounds within the same run at `F30AA029`), both attempts fail.

Evidence that this is a prompt-structure issue: the same sha256 hash for the canned response appears across multiple independent runs and rounds, meaning Claude consistently produces an identical unhelpful reply in this failure mode.

## Evidence

- `skills/fluff-analysis/scripts/fluff-analysis.py` runs `E14AFC53` and `F30AA029` show `execution-issues.md` warnings:
  - `voter_tool=claude`, `judge_error_count=15/15` (E14AFC53), `judge_error_count=9/9` and `12/12` (F30AA029).
  - First 200 bytes of voter output: `"Ready to review. Please share the plan modifications or findings you'd like me to vote on."` (sha256 `fb4cc488...`).
- Current run (217EEAF8, issue #5643) voter tally: `Claude | 0 eligible | 11 missing | n/a agreement`.
- `plan_review_panel.py:978-983` — `NOT_SUBSTANTIVE` from `check_voter_parse_rate` demotes the voter to failed.
- `plan_review_panel.py:1001-1019` — fires the degraded warning when `effective < _PLAN_VOTER_PANEL_SIZE`.
- `voting.py:1985-2062` — `check_voter_parse_rate` triggers when `judge_error_count / len(ids) >= _judge_error_parse_threshold()`.
- `agents.py:6282-6293` — `launch_claude_subprocess_main` prepends `_CLAUDE_REVIEW_READ_ONLY_PREAMBLE` and passes the full prompt via stdin to `claude --print`.
- `plan_review_panel.py:583-617` — `_make_voter_prompt` renders the voter prompt and verifies it contains "Read the ballot from this path"; prompt render succeeds (no `RuntimeError`), so the ballot path is in the prompt.

## Affected files

- `python/larch/review/plan_review_panel.py` — voter dispatch, `_parse_rate_retry`, degraded-panel detection.
- `python/larch/agents/agents.py` — `launch_claude_review_main`, `launch_claude_subprocess_main`, `_with_claude_read_only_preamble`.
- `python/larch/review/voting.py` — `check_voter_parse_rate`, `parse_rate_retry_main`.
- Voter prompt template rendered by `python/cli.py render voter` — may need a prompt adjustment to make the expected action unambiguous.

## Suggested fix(es)

1. **Prompt hardening**: Modify the rendered voter prompt or the `_with_claude_read_only_preamble` preamble to explicitly instruct Claude to act immediately without waiting for additional input. For example, add a directive such as "Proceed immediately: read the ballot file at the path below and cast your votes. Do not acknowledge this message or ask for further input." Ensure the ballot path and expected output format are embedded directly in the prompt.

2. **Inline ballot content**: Instead of instructing Claude to use `Read` to fetch the ballot, embed the ballot content directly in the voter prompt. This removes the dependency on a tool call succeeding and eliminates the ambiguity about whether Claude should wait.

3. **Retry on `NOT_SUBSTANTIVE` with a clarifying prompt**: The existing `parse-rate-retry` path already retries on `NOT_SUBSTANTIVE`. Verify that the retry uses a different (more direct) prompt prefix or includes the ballot inline on the retry attempt, so a second canned response is unlikely.

4. **Investigate `_judge_error_parse_threshold()`**: Check whether the threshold is set too loosely, allowing a voter that produces zero valid votes to still reach the retry path rather than failing immediately.

## Open questions

- Does the canned response come from a specific model version or context-window pressure? The same sha256 appearing across independent runs suggests a stable model behavior that can be addressed by prompt change.
- Is `--read-tools-add-dir` + `--permission-mode plan` the right combination for a voter that needs only to read a single file? Passing the ballot content inline may be both simpler and more reliable.
- Does the `parse-rate-retry` actually re-launch a new Claude subprocess, or does it re-parse the same output file? If it re-parses the same file, it can never recover from a `NOT_SUBSTANTIVE` output.

## Test plan
(no test plan section in plan-file)
