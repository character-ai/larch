# launch-claude-drafter.sh — contract

Launches a Claude subprocess for `/design` Step 2b plan drafting. The subprocess may inspect the repository with side-effect-free tools; the launcher owns all writes to `$DESIGN_TMPDIR/plan.txt`, optional `$DESIGN_TMPDIR/plan-summary.md`, and launcher status sidecars.

## CLI

Required flags:

- `--model MODEL` — one non-empty token with no whitespace/control characters.
- `--prompt-file FILE` — existing regular file under `$DESIGN_TMPDIR` or the plugin root.
- `--output-file FILE` — status KV file path under `$DESIGN_TMPDIR`.
- `--timeout SECONDS` — positive integer, capped at `1800`.
- `--design-tmpdir DIR` — existing non-symlink directory; canonicalized with `pwd -P`.
- `--repo-root DIR` — existing non-symlink repository directory; canonicalized with `pwd -P`.

Optional flags:

- `--timing-task-kind KIND` — defaults to `claude-plan-draft`.
- `--baseline-porcelain FILE` — an optional baseline `git status --porcelain` snapshot under `$DESIGN_TMPDIR`.

The launcher intentionally rejects larch wrapper-only flags such as `--read-tools` and `--read-tools-add-dir`; it invokes the native `claude` CLI directly.

## Native Claude argv

The production argv is recorded exactly in `${output}.meta` as `CMD_JSON` and uses only native Claude CLI flags verified from local `claude --help`:

```text
claude --model <model> --print --output-format json --add-dir <repo-root> --allowedTools Read,Glob,Grep,LS --permission-mode plan
```

The allowlist grants repository discovery only. Mutating tools such as `Write`, `Edit`, and `Bash` are not granted, and `--permission-mode plan` is always present.

## Prompt and untrusted data

Step 2b builds the prompt in `$DESIGN_TMPDIR/step2b-drafter-prompt.txt`, including trusted orchestration requirements plus redacted untrusted artifact blocks. The prompt must instruct the subprocess not to write repository or tmpdir files. The launcher reads only the prompt file and writes only its output/status artifacts.

## Output contract

`${output}` remains authoritative fixed-key status data; model prose is never promoted into that path. On success it contains at least:

```text
STATUS=OK
PLAN_WRITTEN=true
PLAN_LINES=<N>
DIFF_LINES=<N>
SUMMARY_WRITTEN=true|false
DRAFTER_LAUNCHED=true
```

On failure it reports `STATUS=ERROR`, `PLAN_WRITTEN=false`, and a fixed `REASON=` such as `CLAUDE_JSON_RESULT_INVALID` or `DELIMITER_EXTRACTION_INVALID`.

Sidecars:

- `${output}.meta` — `CMD_JSON`, timeout, and tool metadata.
- `${output}.stderr` — raw subprocess stderr.
- `${output}.stderr-tail` — redacted failure tail when available.
- `${output}.failure-diag` — failure diagnostic when available.
- `${output}.done` — numeric exit code.
- `${output}.dirty-tree` — dirty-tree evidence contract.

Any JSON envelope or extracted `.result` is scratch-only and removed before exit; there is no persistent `.result` sidecar.

## JSON promotion and delimiter parsing

Claude is run with `--output-format json`. A successful subprocess must produce valid JSON with `is_error` absent/false and a non-empty string `.result`; invalid JSON, `is_error:true`, missing/non-string/empty `.result`, or 0-byte promoted result fails closed with `CLAUDE_JSON_RESULT_INVALID`, exit `99`, and no token-ledger row.

The `.result` text is parsed from scratch with exact whole-line sentinels:

- `LARCH_PLAN_BEGIN` / `LARCH_PLAN_END` — required exactly once.
- `LARCH_SUMMARY_BEGIN` / `LARCH_SUMMARY_END` — optional, but when present must be exactly one balanced non-empty pair.

Missing, duplicate, reversed, nested (summary inside plan or plan inside summary), or unbalanced sentinel pairs fail closed. The sentinel names may appear inside prose when they are not exact whole lines. The extracted plan must be non-empty and its final line must match `diff_lines: <N>`. The launcher atomically writes `plan.txt`, and writes `plan-summary.md` only when a non-empty summary block is present.

## Dirty-tree sidecar

The `.dirty-tree` EXIT trap is installed only after `--output-file` has been canonicalized and containment-validated. Earlier argv/path failures may exit without this sidecar.

When the subprocess never started, the sidecar reports `STATUS=unknown MODE=prelaunch`. After launch:

- With a readable baseline, no diff vs current porcelain reports `STATUS=clean MODE=baseline-delta`; any delta reports `STATUS=dirty MODE=baseline-delta`; git failure reports `STATUS=unknown MODE=baseline-delta`.
- Without a usable baseline, an empty current porcelain reports `STATUS=clean MODE=absolute`; non-empty porcelain reports `STATUS=unknown MODE=no-baseline` rather than confirmed dirty.

Step 2b treats only `STATUS=dirty MODE=baseline-delta` as confirmed new drafter mutations.

## Token and timing rows

After JSON promotion and delimiter extraction succeed, the launcher records `token-ledger.sh record-vendor claude_sub ... raw=<role>`, with `raw` derived locally from `--timing-task-kind` (`claude_draft`, `claude_scout`, `claude_vote`, or `claude_review`). Timing is recorded with vendor `claude` and the supplied task kind. JSON/delimiter failures skip token recording.

Regression harness: `scripts/test-launch-claude-drafter.sh`.
