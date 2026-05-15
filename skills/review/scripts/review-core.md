# review-core.sh Contract

`skills/review/scripts/review-core.sh` runs one `/review` round. It is not a long-running loop and does not apply fixes. The `/review` `SKILL.md` wrapper owns the outer round loop, invokes `/review-and-fix` when `REVIEW_CORE_STATUS=fix-required`, runs relevant checks, classifies substantiality, and decides whether to call `review-core.sh` again.

Accepted flags:

- `--mode diff|description`
- `--output-dir DIR`
- `--session-env-path PATH`
- `--codex-available true|false`
- `--cursor-available true|false`
- `--diff-file PATH`
- `--commit-count N`
- `--scope-files PATH`
- `--plan-file PATH`
- `--feature-file PATH`
- `--description-text TEXT`
- `--panel simple|hard` (default `hard`)
- `--run-id ID`
- `--round-num N` (default `1`)

The script emits only `KEY=value` records on the lib-quiet FD3 contract stream. Ordinary stdout/stderr is redirected by `scripts/lib-quiet.sh` unless quiet mode is disabled.

Emitted keys:

- `REVIEW_CORE_STATUS=ok|fix-required|zero-findings|cap-reached|wholesale-rejected`
- `ROUND_NUM`
- `ACCEPTED_COUNT`
- `REJECTED_COUNT`
- `FINDINGS_FILE`
- `ACCEPTED_FINDINGS_FILE`
- `REJECTED_FINDINGS_FILE`
- `PANEL_MODE=normal|both-down`
- `PANEL_SHAPE=simple|hard`

Round stages:

1. Gather context with `gather-context.sh --mode <mode> --output-dir "$REVIEW_TMPDIR"`.
2. Dispatch the reviewer panel with `dispatch-panel.sh --mode "$MODE" --review-tmpdir "$REVIEW_TMPDIR" --panel "$PANEL"`.
3. Collect findings, run dirty-tree recovery, tally votes, detect wholesale rejection, and emit tally artifacts.
4. Copy parent tmpdir artifacts when `SESSION_ENV_PATH` is set.

Artifact paths under `$REVIEW_TMPDIR`:

- `findings.md`
- `accepted-findings.md`
- `rejected-findings.md`
- `oos-accepted-review.md`
- `review-round-summary.md`
- `review-summary.json`
- `review-dirty-tree-summary.env`

When `SESSION_ENV_PATH` is set, `emit-tally.sh` copies `review-round-summary.md` and `review-summary.json` to `$(dirname "$SESSION_ENV_PATH")`. `review-core.sh` copies `rejected-findings.md`, `oos-accepted-review.md`, and `review-dirty-tree-summary.env` there.

Dirty-tree recovery runs after collection. It scans every launched reviewer output sidecar `${output}.dirty-tree`; missing sidecars count as `unknown`. Any `STATUS=dirty` or `STATUS=unknown` marks `ANY_DIRTY=true`, records the output basename in `LAUNCHERS_DIRTY`, runs `scripts/check-mid-run-dirty-tree.sh --mode checkpoint`, and discards reviewer-introduced paths named by sidecar path streams (`TRACKED_PATHS_FILE`, `NEW_UNTRACKED_PATHS_FILE`) when a recovery checkpoint reports dirty or unknown. The summary file contains `ANY_DIRTY`, `LAUNCHERS_DIRTY`, `RECOVERY_TAKEN`, and any per-launcher path stream keys.

Run-log batches are not written here. The `/review` wrapper owns `log-phase.sh` calls after summary artifacts are complete.

Known gap deferred to Part 2: `skills/review/references/heavy-worker.md` still documents heavy-worker Step 1 as `gather-branch-context.sh`, while inline `review-core.sh` uses `gather-context.sh` to match the current inline path. This PR documents the divergence rather than changing heavy-worker behavior.

Harness: `skills/review/scripts/test-review-core.sh`, wired through `make test-review-core`. The harness uses environment-variable seams (`REVIEW_CORE_*_SH`) to stub helper scripts without launching external reviewers.
