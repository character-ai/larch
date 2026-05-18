# review-core.sh Contract

`skills/review/scripts/review-core.sh` runs one review round. It is not a long-running loop and does not apply fixes. The `/review` `SKILL.md` wrapper and `/implement` Step 5's `review-and-fix.sh --implement-tmpdir` mode own their respective outer round loops, fix application, relevant checks, substantiality classification, and decisions about whether to call `review-core.sh` again.

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
- `--dynamic-archetypes N` (`0..4`, default `0`; overrides `LARCH_DYNAMIC_ARCHETYPES_MAX`)
- `--run-id ID`
- `--round-num N` (default `1`)

After `gather-context.sh`, resolved `--scope-files` (explicit flag or `FILE_LIST_FILE` when the flag was unset) and `--plan-file`, when non-empty and the scope file has content / the plan path exists, are forwarded to `tally-code-votes.sh` so the scope-fit gate can treat plan-mentioned paths as in-scope.

The script emits only `KEY=value` records on the lib-quiet FD3 contract stream. Ordinary stdout/stderr is redirected by `scripts/lib-quiet.sh` unless quiet mode is disabled.

Emitted keys:

- `REVIEW_CORE_STATUS=ok|fix-required|zero-findings|cap-reached|panel-failed|main-agent-vote-required`
- `ROUND_NUM`
- `ACCEPTED_COUNT`
- `REJECTED_COUNT` — strictly `rejected` outcomes only; does not include exonerated or neutral.
- `EXONERATED_COUNT` — findings with outcome `exonerated`.
- `NEUTRAL_COUNT` — findings with outcome `neutral`.
- `FINDINGS_FILE`
- `ACCEPTED_FINDINGS_FILE`
- `REJECTED_FINDINGS_FILE`
- `PANEL_MODE=waterfall|normal` (`waterfall` is the current value; `normal` may appear on the zero-scope early-exit path)
- `PANEL_SHAPE=simple|hard`
- `SCOUT_STATUS` — `na` when dynamic archetypes are disabled; otherwise copied from `dispatch-panel.sh` and emitted on every post-dispatch exit path.
- `DYNAMIC_SLOTS=N` — queued dynamic reviewer slots; emitted on every post-dispatch exit path.
- `SCOUT_MANIFEST=PATH` — present when a scout manifest exists.
- `YIELD_TSV_FILE=PATH` — present when `tally-code-votes.sh --manifest-file` writes per-archetype yield metrics.
- `VOTING_SKIPPED_WARNING=<text>` — emitted only on the 0-judge main-agent-required path; callers should parse and display it as a user-visible warning
- `OUT_OF_SCOPE_DRIFT_COUNT=N` — number of in-scope findings reclassified to OOS by the scope-fit gate in `tally-code-votes.sh`; copied from tally stdout when voting runs; `0` on early exits that skip tally (description zero-scope, `panel-failed`, `zero-findings` after collection, or before the tally stage).

Diff-mode convergence note: `REVIEW_CORE_STATUS=ok` is also the expected outcome when voting leaves `ACCEPTED_COUNT=0` and one or more findings were rejected. Callers that need to distinguish "nothing left to fix after voting" from a benign no-follow-up outcome should monitor `ACCEPTED_COUNT` together with `REJECTED_COUNT`, `EXONERATED_COUNT`, and `NEUTRAL_COUNT`, not the status string alone.

Round stages:

1. Gather context with `gather-context.sh --mode <mode> --output-dir "$REVIEW_TMPDIR"`.
2. Dispatch the reviewer panel with `dispatch-panel.sh --mode "$MODE" --review-tmpdir "$REVIEW_TMPDIR" --panel "$PANEL" --dynamic-archetypes "$DYNAMIC_ARCHETYPES"`.
3. Collect findings, run dirty-tree recovery, tally votes, and emit tally artifacts. If the tally emits `TALLY_STATUS=main-agent-vote-required`, skip `emit-tally.sh`, emit `REVIEW_CORE_STATUS=main-agent-vote-required`, and hand the findings ballot back to the caller for main-agent adjudication.
4. Copy parent tmpdir artifacts when `SESSION_ENV_PATH` is set.

Artifact paths under `$REVIEW_TMPDIR`:

- `findings.md`
- `accepted-findings.md`
- `rejected-findings.md`
- `oos-accepted-review.md`
- `review-round-summary.md`
- `review-summary.json`
- `review-dirty-tree-summary.env`
- `scout-round<N>-status.env`
- `scout-archetype-yield.tsv` when a panel manifest was available for yield attribution

When `SESSION_ENV_PATH` is set, `emit-tally.sh` copies `review-round-summary.md` and `review-summary.json` to `$(dirname "$SESSION_ENV_PATH")`. `review-core.sh` copies `rejected-findings.md`, `oos-accepted-review.md`, and `review-dirty-tree-summary.env` there.

When `IMPLEMENT_TMPDIR` and `RUN_ID` are set, `review-core.sh` best-effort calls
`scripts/larch-log.sh write-round --skill implement --round "$ROUND_NUM"
--source-dir "$REVIEW_TMPDIR"` before emitting the terminal round status. This
persists registered per-round reviewer outputs, vote files, sidecars, and
summary artifacts under `larch-logs/implement/<RUN_ID>/round-<N>/`; the existing
later `larch-log.sh commit` flush owns committing those files.

Dirty-tree recovery runs after collection. It scans every launched reviewer output sidecar `${output}.dirty-tree`; missing sidecars count as `unknown`. Any `STATUS=dirty` or `STATUS=unknown` marks `ANY_DIRTY=true`, records the output basename in `LAUNCHERS_DIRTY`, runs `scripts/check-mid-run-dirty-tree.sh --mode checkpoint`, and discards reviewer-introduced paths named by sidecar path streams (`TRACKED_PATHS_FILE`, `NEW_UNTRACKED_PATHS_FILE`) when a recovery checkpoint reports dirty or unknown. The summary file contains `ANY_DIRTY`, `LAUNCHERS_DIRTY`, `RECOVERY_TAKEN`, and any per-launcher path stream keys.

Run-log batches are not written here. The `/review` wrapper owns `log-phase.sh` calls after summary artifacts are complete; `review-core.sh` only emits `SCOUT_MANIFEST`, `SCOUT_STATUS`, `DYNAMIC_SLOTS`, and `YIELD_TSV_FILE` for the wrapper to consume. Description-mode zero-scope exits still emit `SCOUT_STATUS=na`, `DYNAMIC_SLOTS=0`, and an empty `SCOUT_MANIFEST` so wrappers can parse a stable KV contract.

Known gap deferred to Part 2: `skills/review/references/heavy-worker.md` still documents heavy-worker Step 1 as `gather-branch-context.sh`, while inline `review-core.sh` uses `gather-context.sh` to match the current inline path. This PR documents the divergence rather than changing heavy-worker behavior.

Harness: `skills/review/scripts/test-review-core.sh`, wired through `make test-review-core`. The harness uses environment-variable seams (`REVIEW_CORE_*_SH`) to stub helper scripts without launching external reviewers.
