# run-step3-review.sh

**Consumer**: `/design` Step 3 — deterministic plan-review phase driver wrapping `plan-review-loop.sh`.

**Caller**: `skills/design/SKILL.md` Step 3 (uncaptured `--preview-only` fence for live preview; captured `--no-preview` fence for review KVs).

## Argv

| Flag | Required | Notes |
|------|----------|-------|
| `--design-tmpdir PATH` | yes | Raw path in `--preview-only`; validated with `cd … && pwd -P` in `--no-preview` |
| `--preview-only` | no | Render preview live; owns `.step3-entry-plan-printed` sentinel; no `--round-cap` needed |
| `--no-preview` | no | Default when neither flag given; requires `--round-cap`; runs cap guard + review |
| `--round-cap N` | `--no-preview` only | Orchestrator expands `${LARCH_DESIGN_ROUND_CAP:-5}` |

`--preview-only` and `--no-preview` are mutually exclusive (exit 2 when both supplied). Omitting both defaults to `--no-preview` for backward compatibility.

The driver does **not** re-read `LARCH_DESIGN_*` env vars (except `RUN_STEP3_EMIT_PREVIEW_SH` seam in preview mode).

## Derived / session inputs

- Tier cap via `read-design-classification.sh` on `$DESIGN_TMPDIR/run-params.json` (SIMPLE = 3 review runs, HARD = 5). (`--no-preview` only)
- `CODEX_PRESENT`, `CURSOR_PRESENT`, optional `IMPLEMENT_TMPDIR` from the orchestrator session (not read from files inside the driver).
- `$DESIGN_TMPDIR/plan.txt`, `review-round-count.txt`, `.step3-review-cap.env`, `.step3-plan-review-result.env`.

## Responsibilities

0. **`--preview-only`** — live FD-3 preview via `emit`; driver owns `.step3-entry-plan-printed` with output-string + allowlist touch rules. `--preview-only` needs only `--design-tmpdir` (raw path to renderer); `--round-cap` and canonicalized tmpdir `cd` apply only to `--no-preview`. `larch_design_tmpdir_validate` gates sentinel read/write/touch; stale sentinel on invalid tmpdir does not suppress warnings. Renderer path: `RUN_STEP3_EMIT_PREVIEW_SH` override seam (default: `emit-design-plan-preview.sh`).
1. Review-round cap entry guard → `.step3-review-cap.env`
2. Symlink-safe `plan-review/round-*` cleanup
3. HARD round-cursor read/advance via `snapshot-plan-round.sh`
4. Pending round persist to `review-round-count.txt` before launch
5. Foreground `plan-review-loop.sh` (`RUN_STEP3_PLAN_REVIEW_LOOP_SH` override for tests)
6. Parse `.step3-plan-review-result.env` + stdout fallback; normalize `LOOP_STATUS`
7. Persist vs rollback `review-round-count.txt` on `tally-error` / `degraded-empty-collector`
8. Atomic write `$DESIGN_TMPDIR/.step3-review-result.env` + `emit_kv` breadcrumbs

## Normalized result env (`.step3-review-result.env`)

`LOOP_STATUS`, `TALLY_PLAN_REVIEW_STATUS`, `STEP3_REVIEW_CAP_REACHED`, `STEP3_REVIEW_ROUND_NUM`, `ROUND_NUM`, `ACCEPTED_COUNT`, `IMPORTANT_ACCEPTED_COUNT`, `DEGRADED_PANEL`, `ROUNDS_COMPLETED`, `AGGREGATOR_STATUS`, `VOTING_TALLY_FILE`, `REVIEW_ROUND_COUNT`.

## Exit codes

| Code | When |
|------|------|
| `0` | Normal completion (any settled `LOOP_STATUS`) |
| `1` | HARD `snapshot-plan-round.sh` write-cursor failure before review launch (`panel-failed` handoff in `.step3-review-result.env`; orchestrator continues into the Step 3 branch matrix — not a hard SKILL fence abort; round count rolled back) or refusal to write symlinked `.step3-review-result.env` (normalized `emit_kv` breadcrumbs still emitted on stdout) |
| `2` | Argv / missing executable inner loop |

## Idempotency

No `--resume-from`. Caller-owned `.completed/step-3` sentinel plus `review-round-count.txt` persist/rollback semantics unchanged.

## LLM boundary

Stops before semantic finding dedup (#6), Gate B (Step 3.5), and `main-agent-vote-required` ballot adjudication — those remain in `SKILL.md`.

## Harness

`skills/design/scripts/test-run-step3-review.sh` (stub: `test-run-step3-review.md`).

`skills/design/scripts/test-step3-orchestrator-fence.sh` (stub: `test-step3-orchestrator-fence.md`) — mirrors the Step 3 orchestrator handoff fence in `SKILL.md` (result env allowlist, stdout merge, `LOOP_STATUS` normalization, exit `2`).
