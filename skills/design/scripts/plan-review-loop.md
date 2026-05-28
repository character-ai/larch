# plan-review-loop.sh

**Consumer**: `/design` Step 3 — multi-round plan-review driver (legacy single-pass when `--round-cap` is omitted on argv).

**Primary callers**: `skills/design/SKILL.md` Step 3 (foreground Bash block).

## Invariants

Validates `$DESIGN_TMPDIR` via `larch_design_tmpdir_validate` after the required-arg check, before resolving the path with `cd ... && pwd -P`.

- Writes session-root artifacts under `$DESIGN_TMPDIR/`: `ballot.txt`, `accepted-plan-findings.md`, `rejected-findings.md`, `oos.md`, `oos-accepted-design.md`, `voting-tally.md`. `ballot.txt` is created or truncated on every exit path (including `panel-failed` and zero-finding short-circuit) so consumers avoid `ENOENT`. Never revises `plan.txt` in legacy mode; multi-round mode auto-applies via `revise-plan-with-waterfall.sh` when `manual_gate_b=false`.
- In multi-round mode, `oos-accepted-design.md` is cumulative across settled rounds. Zero-finding, tally-error, and panel-failed branches preserve the prior cumulative file instead of truncating it, and only accepted OOS blocks are merged forward.
- Honors `LARCH_AGGREGATOR_DISABLED=1` by skipping `aggregate-findings.sh` and setting `AGGREGATOR_STATUS=disabled`.
- Emits stdout KV lines documented below plus optional `WARN=` lines.
- Writes `$DESIGN_TMPDIR/plan-review/round-<N>/findings-classification.tsv` for normal tally runs; header-only TSV on empty-artifact exits.
- Writes `$DESIGN_TMPDIR/.step3-plan-review-result.env` at every terminal exit (multi-round and legacy).
- Per-round forensics allowlist: `scripts/lib-design-round-artifacts.md`.
- Allowed snapshot inputs must be regular files. If an allowlisted session-root artifact resolves as a symlink, the new snapshot payload is discarded, pre-existing `round-N/revise/` forensics are preserved, and terminal statuses keep their original `LOOP_STATUS` while appending `snapshot-failed` to `REASON` when the failure happens after a terminal outcome has already been determined.

## Argv

`--design-tmpdir`, `--plan-file`, optional `--feature-file`, `--round-num` (starting round; default 1), optional `--round-cap N` (enables multi-round when present on argv; default value from `LARCH_DESIGN_ROUND_CAP` only applies when the flag is passed), optional `--convergence-threshold N` (default `${LARCH_DESIGN_CONVERGENCE_THRESHOLD:-3}`), `--codex-present`, `--cursor-present`, optional `--timeout` (default 1860), `--help`.

**Legacy contract**: omit `--round-cap` → single pass, `LOOP_STATUS=complete`, no inner revise loop.

## Machine output (stdout)

| Key | When set |
|-----|----------|
| `LOOP_STATUS` | Always |
| `ACCEPTED_COUNT` | Always |
| `IMPORTANT_ACCEPTED_COUNT` | Always |
| `DEGRADED_PANEL` | Always |
| `ROUNDS_COMPLETED` | Always |
| `AGGREGATOR_STATUS` | Always |
| `TALLY_PLAN_REVIEW_STATUS` | Always |
| `VOTING_TALLY_FILE` | Always |
| `VOTER_1_PARSE_RATE_STATUS` | Always |
| `CONVERGENCE_STREAK` | Multi-round |
| `REASON` | When annotated (`zero-findings`, `zero-findings-degraded-panel`, `streak`, `cap-hit`, `revision-failed`, `manual-gate-b`, etc.) |
| `REVISE_STATUS` | Multi-round revise path |
| `COLLECT_OK_COUNT` / `COLLECT_FAILURE_COUNT` | Multi-round |

`LOOP_STATUS` values: `complete`, `converged`, `cap-hit`, `zero-findings-degraded-panel`, `revision-failed`, `tally-error`, `degraded-empty-collector`, `plan-size-trigger`, `plan-validator-defects`, `emit-plan-failed`, `panel-failed`, `main-agent-vote-required`.

## Durable handoff: `.step3-plan-review-result.env`

Normalized KVs for SKILL.md Step 3.5 and Gate B across Bash fence boundaries. Values use a controlled vocabulary (no raw user content). See `plan-review-loop.sh` function `write_step3_result_env`.

## `round-summary.env` schema

Written under `plan-review/round-N/round-summary.env` after each round's outcome is known. Keys: `ROUND_NUM`, `LOOP_STATUS` (terminal rounds only), `REASON`, `CONVERGENCE_STREAK`, `ACCEPTED_COUNT`, `IMPORTANT_ACCEPTED_COUNT`, `DEGRADED_PANEL`, `TALLY_PLAN_REVIEW_STATUS`, `AGGREGATOR_STATUS`, `REVISE_STATUS`, `REVISE_WINNING_TIER`, `PLAN_HASH_BEFORE_REVISE`, `PLAN_HASH_AFTER_REVISE`, `COLLECT_OK_COUNT`, `COLLECT_FAILURE_COUNT`. Successful tier-4 fallback rounds preserve `REVISE_STATUS=ok-fallback` here instead of being normalized to `ok`.

## Exit codes

| Code | `LOOP_STATUS` |
|------|----------------|
| 0 | `converged`, `cap-hit`, `zero-findings-degraded-panel`, `revision-failed`, `main-agent-vote-required`, `complete`, `tally-error`, `degraded-empty-collector`, `plan-size-trigger`, `plan-validator-defects`, `emit-plan-failed` |
| 1 | `panel-failed` |
| 2 | argv error |

## Cross-links

- `scripts/lib-design-round-artifacts.md` — snapshot/publish allowlist
- `revise-plan-with-waterfall.md` — `REVISE_STATUS` contract
- `aggregate-findings.md` — `--allow-findings-outside-tmpdir true`
- `tally-plan-review.md`, `dispatch-plan-voters.md`

## Cross-entry forensic limitation

Each Step 3 entry clears `plan-review/round-*/` before launch (SKILL.md); prior Step 3 entry forensics are not retained across Gate C re-runs.

## Makefile

`make test-plan-review-loop` — see `skills/design/scripts/test-plan-review-loop.sh`.

`make test-design-multi-round-integration` — cross-script harness.

## Edit-in-sync

Keep this file aligned with `plan-review-loop.sh` behavior and argv.
