# Plan-Quality Assessor (HARD-only)

**Consumer**: `/design` Step 3.6 between Gate B settled paths and Step 3b.

**When it fires**: HARD-only (`workflow_path=HARD` re-read from `run-params.json` each invocation), round ≥ 2 (per `plan-review-round-cursor.txt`), on every Gate B settled path — Apply all, Go through each (without abort), zero-findings short-circuit. Switch-to-discussion-mode returns to Gate A and does **not** traverse Step 3.6.

## Artifacts (top-level under `$DESIGN_TMPDIR`)

| File | Purpose |
|------|---------|
| `plan.txt-original` | Write-once anchor at first HARD plan emit (Step 2b) |
| `plan-after-round-<N>.txt` | Write-once snapshot after Gate B settles (Step 3.6 `write-after`) |
| `plan-review-round-cursor.txt` | Integer round; Step 3 reads and may advance |
| `assessor-verdict-round-<N>.txt` | `NOT_WORSE` or `WORSE: <justification>` |
| `assessor-verdict-round-<N>.env` | Tally KV block + `QUALIFICATIONS_SUMMARY` |

No `plan-review/round-<N>/` subdirectory — design-log harvest uses `find -maxdepth 1`.

## Round cursor (FINDING_2)

At Step 3 entry (HARD-only): if `plan-after-round-<cursor>.txt` exists, advance cursor to `cursor+1` before `plan-review-loop.sh`. Cursor parsing normalizes leading-zero decimal inputs before arithmetic, and a failed `write-cursor` aborts Step 3 before review launch rather than letting shell state diverge from `plan-review-round-cursor.txt`. Step 3.6 re-reads the cursor file unconditionally, preflights `feature-description.txt`, and calls `write-after` for the current round after Gate B; a failed `write-after` aborts before assessor dispatch.

## Strict tally (FINDING_3 + FINDING_8)

Among successful assessors (parseable BETTER/WORSE/TIE): TIE counts toward `EFFECTIVE_ASSESSORS` but not `worse_count` / `better_count`.

WORSE-majority when: (3 successful, worse≥2) OR (2 successful, worse=2) OR (1 successful, worse=1). Else NOT_WORSE. Zero successful → NOT_WORSE (fail-open).

Examples (BETTER, TIE, WORSE): (0,0,3)→WORSE; (0,1,2)→WORSE; (1,0,2)→WORSE; (0,2,1)→NOT_WORSE; (1,1,1)→NOT_WORSE.

## Operator UX (FINDING_15)

On `ASSESSOR_VERDICT=worse-majority` with `ASSESSOR_STATUS=ok` and `EFFECTIVE_ASSESSORS >= 1`: show verdict file + `QUALIFICATIONS_SUMMARY` from `.env`, then `AskUserQuestion` **Continue** / **Stop**.

- **Continue** → Step 3b unchanged.
- **Stop** → `SUMMARY_OUTCOME=cancelled-assessor-worse`, Final summary, preserve `$DESIGN_TMPDIR`, no `[DESIGNED]` rename, no design-log publish.

On `EFFECTIVE_ASSESSORS=0`: proceed as NOT_WORSE; print `**⚠ 3.6: 0/3 effective assessors; proceeding without quality gate (round <N>, see assessor-verdict-round-<N>.env).**` — no Continue/Stop prompt. Dispatch or tally failures must still leave a verdict `.env` behind via degraded-default-open synthesis so the warning points to a real artifact.

## Cursor narration backstop (#2995)

`dispatch-plan-assessors.sh` passes `--require-result-pattern` matching `ASSESSMENT:` so narration-only Cursor output fails through the waterfall.

## Scripts

- `skills/design/scripts/snapshot-plan-round.sh`
- `skills/design/scripts/dispatch-plan-assessors.sh`
- `skills/shared/scripts/render-assessor-prompt.sh`
- `skills/design/scripts/tally-plan-assessor.sh`
- `skills/design/scripts/assess-plan-round.sh`

## #2871

Future auto-loop may re-enter assessor each round; today's trigger is operator-driven Gate C(c) → Step 3 re-entry.
