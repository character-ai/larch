# run-step3-review.sh

**Consumer**: `/design` Step 3 — deterministic plan-review phase driver wrapping `plan-review-loop.sh` and, in loop mode, `review-design-step3-loop.sh`.

**Caller**: `skills/design/SKILL.md` Step 3 (uncaptured `--preview-only` fence for live preview; captured `--mode loop` fence via `design-step3-review.sh` for the full multi-round loop). `--mode single` is no longer accepted; use `--no-preview` or omit `--mode` for single-round behavior.

## Argv

| Flag | Required | Notes |
|------|----------|-------|
| `--design-tmpdir PATH` | yes | Raw path in `--preview-only`; validated with `cd … && pwd -P` in review modes |
| `--preview-only` | no | Render preview live; owns `.step3-entry-plan-printed` sentinel |
| `--no-preview` | no | Single-round mode; backward-compatible (do not pass `--mode single`) |
| `--mode loop` | no | Run every review round until terminal or bail-out. `--mode single` is rejected; omit `--mode` or use `--no-preview` for single-round behavior. |
| `--starting-round N` | loop only | Resume a loop bail-out at a recorded intra-round phase. Omitted loop starts at `review-round-count.txt + 1`. |

`--preview-only` is mutually exclusive with review modes. `--round-num` is deliberately rejected; the driver derives the artifact round and review-round counter itself.

## Loop mode

`--mode loop` sources `review-design-step3-loop.sh` and calls `run_design_step3_loop()`. The loop invokes the same shared round body used by single-round mode, so `run-step3-review.sh` remains the sole writer of `review-round-count.txt`.

Resume validation follows the last-consumed-round contract:

- omitted `--starting-round` starts at `review-round-count.txt + 1`;
- `--starting-round == count + 1` is a fresh review pass and does not need phase evidence;
- `--starting-round <= count` must have `$DESIGN_TMPDIR/.step3-round-N.phase`;
- `--starting-round > count + 1` is rejected.

The loop emits `STEP3_REVIEW_LOOP_STATUS` with values `complete`, `cap-hit`, `main-agent-vote-required`, `main-agent-apply-required`, `per-round-approval-required`, `postplan-operator-required`, `postplan-failed`, `panel-failed`, `tally-error`, or `degraded-empty-collector`.

## Single-round responsibilities

0. **`--preview-only`** — live FD-3 preview via `emit`; driver owns `.step3-entry-plan-printed` with output-string + allowlist touch rules.
1. Review-round cap entry guard → `.step3-review-cap.env`.
2. Symlink-safe cleanup of only the active `plan-review/round-<ROUND_NUM>` slot before launch.
4. Pending round persist to `review-round-count.txt` before launch.
5. Foreground `plan-review-loop.sh` (`RUN_STEP3_PLAN_REVIEW_LOOP_SH` override for tests), passing both `--round-num "$ROUND_NUM"` and `--prune-round-num "$STEP3_REVIEW_ROUND_NUM"`.
6. Parse `.step3-plan-review-result.env` + stdout fallback; normalize `LOOP_STATUS`.
7. Persist vs rollback `review-round-count.txt` on `tally-error` / `degraded-empty-collector`.
8. Atomic write `$DESIGN_TMPDIR/.step3-review-result.env` + `emit_kv` breadcrumbs.

The cap warning remains boundary-qualified: `**⚠ Step 3: review-round cap (<cap>) reached for <tier>; skipping panel and continuing to Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4, then Gate C.**`

## Normalized result env (`.step3-review-result.env`)

`LOOP_STATUS`, `TALLY_PLAN_REVIEW_STATUS`, `STEP3_REVIEW_CAP_REACHED`, `STEP3_REVIEW_ROUND_NUM`, `ROUND_NUM`, `ACCEPTED_COUNT`, `IMPORTANT_ACCEPTED_COUNT`, `DEGRADED_PANEL`, `ROUNDS_COMPLETED`, `AGGREGATOR_STATUS`, `VOTING_TALLY_FILE`, `REVIEW_ROUND_COUNT`, plus `SCOPE_ANCHOR_FILE` only when forwarded from the inner plan-review result on `ok` / `main-agent-vote-required`.

## Exit codes

| Code | When |
|------|------|
| `0` | Normal completion or loop bail-out envelope |
| `2` | Argv / missing executable inner loop / invalid loop resume |

## Harness

`skills/design/scripts/test-run-step3-review.sh` covers preview behavior, single mode, `--mode loop`, `--starting-round`, exact reject messages, and plan-review-loop argv. `skills/design/scripts/test-review-design-step3-loop.sh` covers the loop controller.

## Scope anchor result env

`run-step3-review.sh` launches plan review against the staged binding scope anchor at `$DESIGN_TMPDIR/plan-review-scope-anchor.txt`. It parses `SCOPE_ANCHOR_FILE` from the inner `.step3-plan-review-result.env` / stdout fallback, validates that the path is a regular non-empty file under `$DESIGN_TMPDIR`, and emits/persists it only when both `TALLY_PLAN_REVIEW_STATUS` is `ok` or `main-agent-vote-required` and `LOOP_STATUS` is `complete` or `main-agent-vote-required`.

## Prune-round threading

`run-step3-review.sh` writes `STEP3_REVIEW_ROUND_NUM` to `review-round-count.txt` before calling `plan-review-loop.sh` and also passes the same value explicitly as `--prune-round-num`. `plan-review-loop.sh` defaults omitted `--prune-round-num` to `--round-num` for direct single-pass callers and no longer reads `review-round-count.txt`.
## Concise prune/log audit update
