# run-step3-review.sh

**Consumer**: `/design` Step 3 — deterministic plan-review phase driver wrapping `plan-review-loop.sh`.

**Caller**: `skills/design/SKILL.md` Step 3 (foreground Bash fence after timing + plan preview).

## Argv

| Flag | Required | Notes |
|------|----------|-------|
| `--design-tmpdir PATH` | yes | Validated with `cd … && pwd -P` |
| `--round-cap N` | yes | Orchestrator expands `${LARCH_DESIGN_ROUND_CAP:-5}` |
| `--convergence-threshold N` | yes | Orchestrator expands `${LARCH_DESIGN_CONVERGENCE_THRESHOLD:-3}` |

The driver does **not** re-read `LARCH_DESIGN_*` env vars.

## Derived / session inputs

- Tier cap via `read-design-classification.sh` on `$DESIGN_TMPDIR/run-params.json` (SIMPLE = 3 review runs, HARD = 5).
- `CODEX_PRESENT`, `CURSOR_PRESENT`, optional `IMPLEMENT_TMPDIR` from the orchestrator session (not read from files inside the driver).
- `$DESIGN_TMPDIR/plan.txt`, `review-round-count.txt`, `.step3-review-cap.env`, `.step3-plan-review-result.env`.

## Responsibilities

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
