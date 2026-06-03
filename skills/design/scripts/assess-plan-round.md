# assess-plan-round.sh

Step 3.6 orchestrator for the HARD-only plan-quality assessor lane. It is the only helper that decides whether to skip, degrade open, or tally the panel and therefore owns the persisted `ASSESSOR_*` status contract consumed by `skills/design/SKILL.md`.

## Inputs and gating

- Reads `workflow_path` from `run-params.json` with a `jq` fast-path and a text fallback so the HARD gate still works when `jq` is unavailable.
- Re-reads the round cursor via `snapshot-plan-round.sh read-cursor`; rounds `< 2` are skipped before any assessor artifacts are touched.
- Requires `plan.txt-original`, `plan-after-round-<N-1>.txt`, `plan.txt`, and `feature-description.txt`.
- Missing required inputs do not dispatch. Instead the helper appends a `Warnings` entry to `execution-issues.md`, emits `ASSESSOR_STATUS=missing-snapshot`, and exits without writing verdict artifacts.

## Dispatch and monitor

- Captures dispatcher stdout KVs in a dedicated file and keeps incidental stderr/breadcrumb noise in the quiet log; control flow must never parse KVs from the quiet log.
- Accepts only top-level assessor output paths rooted in `$DESIGN_TMPDIR` with the expected `claude|codex|cursor-plan-assessor-round-<N>.txt` basenames. Path drift or tampering forces `DISPATCH_OK=false`.
- Breadcrumb monitor failures are recorded as warnings, but they no longer suppress a valid tally when dispatcher KVs and assessor outputs are still usable.

## Outcomes

- `ASSESSOR_STATUS=skipped`: non-HARD workflow or round 1.
- `ASSESSOR_STATUS=missing-snapshot`: required preflight input absent; warning appended.
- `ASSESSOR_STATUS=ok`: tally ran and at least one effective assessor parsed.
- `ASSESSOR_STATUS=degraded-default-open`: dispatch/tally failed, or tally completed with `EFFECTIVE_ASSESSORS=0`.

Successful tally writes:

- `assessor-verdict-round-<N>.txt`
- `assessor-verdict-round-<N>.txt.env`

Fail-open synthesis writes the same artifacts with a `NOT_WORSE` verdict so Step 3.6 warnings always point at a real sidecar.

## Classification override

`--design-classification HARD|SIMPLE` is accepted for callers that already resolved tier with `scripts/read-design-classification.sh`. The explicit override takes precedence over `run-params.json`. When the override is absent, the helper delegates to `read-design-classification.sh`; missing, unreadable, or invalid `design_classification` resolves to HARD. Legacy `workflow_path` cannot suppress assessment when `design_classification` is absent or invalid.
