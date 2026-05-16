# dispatch-code-voters.sh

**Type**: executable script.

**Purpose**: Launch the `/review` code-review 3-judge panel (Claude opus + Codex + Cursor). When an external vendor is unhealthy, launch a Claude voter in its place so the panel always has 3 voters. Writes one vote-output file per voter; the orchestrator (`review-core.sh`) then passes the three files to `tally-code-votes.sh`.

This is the script that closes the auto-accept bug — before this change, `tally-votes.sh` read `cursor-votes.txt` and `codex-votes.txt` that nothing wrote, so voting always fell back to accept-all.

## Args

| Flag | Type | Required | Description |
|---|---|---|---|
| `--ballot-file FILE` | path | yes | Markdown file with `### FINDING_N:` blocks (one per finding). Voters read this from disk; the prompt only carries the path, not the content. |
| `--review-tmpdir DIR` | path | yes | Output directory for vote-output files, prompt-files, and launch logs. |
| `--codex-available true\|false` | enum | yes | If `false`, Voter 2 slot is filled by a Claude replacement (Status=`fallback`). |
| `--cursor-available true\|false` | enum | yes | If `false`, Voter 3 slot is filled by a Claude replacement (Status=`fallback`). |
| `--session-env-path FILE` | path | no | Forwarded for execution-issue logging. |
| `--diff-file FILE` | path | no | When supplied, passed to the Claude voter as `--context-files` so the judge has the patch in context. |
| `--plan-file FILE` | path | no | When supplied, passed to the Claude voter as additional context. |

## Voter slots

| Slot | Tool | Output filename | Notes |
|---|---|---|---|
| Voter 1 | Claude opus | `claude-vote-output.txt` | Always launched; primary judge. Sentinel: `claude-vote-output.txt.done`. |
| Voter 2 | Codex | `codex-vote-output.txt` | When `codex-available=false`, replaced by Claude → `claude-replacement-codex-vote-output.txt`. |
| Voter 3 | Cursor | `cursor-vote-output.txt` | When `cursor-available=false`, replaced by Claude → `claude-replacement-cursor-vote-output.txt`. |

## Output (FD 3 via `emit_kv`)

| Key | Description |
|---|---|
| `VOTER_N_PATH` | Absolute path to vote-output file for slot N (1, 2, 3). |
| `VOTER_N_TOOL` | `claude`, `codex`, or `cursor`. |
| `VOTER_N_STATUS` | `launched` (external dispatched successfully), `fallback` (vendor unhealthy → Claude replacement launched), or `failed` (sentinel reported non-zero exit, or output file missing/empty after wait). |
| `DISPATCH_OK` | `true` when all three sentinels reported exit=0; `false` on any failure. |

## Launch sequence

1. Build a voter prompt per slot (paths to the ballot file, vote-line schema, EXONERATE proportionality guidance).
2. Launch all three voters in parallel:
   - Claude via `launch-claude-subprocess.sh --model claude-opus-4-7`, with `--context-files` set to diff/plan when supplied.
   - Codex via `run-external-agent.sh --tool codex` with `agent-model-args.sh --with-effort` and `--output-last-message`.
   - Cursor via `run-external-agent.sh --tool cursor --capture-stdout` with `agent-model-args.sh --with-effort` and `cursor-auth-flags.sh`.
3. Wait for sentinels via `wait-for-reviewers.sh --timeout 1260`.
4. For each voter, set `VOTER_N_STATUS=failed` if the sentinel reports non-zero exit OR the vote-output file is missing/empty.

## Voter prompt

Each prompt instructs the judge to read the ballot file from disk and emit one line per finding using the same `FINDING_N:` id from the ballot:

```
FINDING_N: YES
FINDING_N: NO -- one-line reason
FINDING_N: EXONERATE -- one-line reason
```

`[OUT_OF_SCOPE]` items use the same `FINDING_N:` line shape — voters interpret YES as "worth filing an issue", per voting-protocol.md OOS Vote Semantics.

## Sentinel parity

External agents (Codex, Cursor) emit `<output>.done` sentinels naturally; the Claude launch path writes a `0\n` sentinel explicitly on success (or the rc on failure) so `wait-for-reviewers.sh` polls all three slots uniformly.

## Callers

- `skills/review/scripts/review-core.sh` — invoked after `collect-findings.sh`. The output files become `--voter-files` arguments to `tally-code-votes.sh`.

## Harness

`scripts/test-dispatch-code-voters.sh` — exercises the dispatch logic with the actual external binaries stubbed out via `LAUNCH_CLAUDE_SUBPROCESS` / `RUN_EXTERNAL_AGENT` env-overrides. (Stubbing pattern mirrors `scripts/test-dispatch-plan-voters.sh`.)
