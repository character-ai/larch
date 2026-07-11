# Discussion Round 1 — #6836 Step 8 assessment bgjob adapter and harness

Partition piece 3/4 of #6801. Firm headings: `skills/implement/scripts/step-8-assessment.sh`, `step-8-assessment.md`, `test-step-8-assessment.sh`, `test-step-8-assessment.md`. Piece 2's CLI (`python/cli.py architectural-assessment run`) already exists and owns materialization, deterministic pre-filter, authoring, persistence, and HEAD-drift handling.

## Decision 1: Adapter scope — thin bgjob envelope only
- **Question**: Should Piece 3's adapter be a thin bgjob envelope over Piece 2's CLI, with zero duplication of Piece 2 logic?
- **Resolution**: Yes. The adapter owns only bgjob start/wait/rejoin, identity validation (requested kind set + covered fingerprint), stale envelope cleanup, and canonical result KVs. It delegates all assessment work to `architectural-assessment run`. It does NOT re-implement materialization, pre-filter, authoring, or persistence.
- **Source**: user

## Decision 2: Fail-closed with one retry on timeout / invalid output
- **Question**: On bgjob timeout (claude delegate exit 124) or Piece 2 invalid/failed output, what must the adapter do?
- **Resolution**: Retry the assessment once at the bgjob level, then fail closed. A second timeout/invalid output emits a fail-closed result KV and stops. Never falls back to main-agent inline authoring. (Note: Piece 2's CLI already retries internally on HEAD drift; the adapter retry is a separate bgjob-level re-launch.)
- **Source**: user

## Decision 3: Stale result on HEAD/kind drift — clear and start fresh
- **Question**: On rejoin, when the existing bgjob result was authored for a different diff fingerprint or requested kind-set (stale due to drift), how should the adapter handle it?
- **Resolution**: Clear the stale bgjob envelope (merge-result + result env) and start a fresh assessment for the current fingerprint/kind-set. Matches "clear stale merge-result state before a fresh launch".
- **Source**: user

## Decision 4: Requested kind-set source
- **Question**: Where does the adapter get the requested assessment kind set?
- **Resolution**: From `DETAIL` in `$IMPLEMENT_TMPDIR/.ship-route-exit-handoff.env` (the existing `NEXT_ACTION=assessments` handoff), comma-separated tokens restricted to `invariants` and `guidelines`. The adapter normalizes/dedupes/orders via the same grammar Piece 2's `normalize_kinds` enforces.
- **Source**: codebase (skills/implement/SKILL.md assessments branch; ship-pr-exit-matrix.md)

## Decision 5: Rejoin identity = requested kind set + covered fingerprint
- **Question**: What constitutes a rejoin match ("only when the fingerprint and requested kind set match")?
- **Resolution**: Rejoin of live/completed work is allowed only when the requested kind set is identical and the covered fingerprint matches. The covered fingerprint reuses Piece 2's existing per-kind materialization identity (`HEAD_SHA` + `BASE_REF` + `DIFF_FINGERPRINT` from each kind's materialize env), composed into one stable digest over the kind set. Exact digest composition is a Step 2b implementation detail; the constraint is: identical kind set + identical covered fingerprint.
- **Source**: codebase (architectural_assessment.py validate_materialization) + user-confirmed constraint

## Decision 6: Canonical result KVs conform to the bgjob result-env contract
- **Question**: What result KVs must the adapter emit and validate?
- **Resolution**: Conform to the standard bgjob result-env contract already used by `step-8-ship.sh` (STEP, BGJOB_RC, plus the merge-result envelope) and add assessment-specific KVs: step identity (`implement-step8-assessment`), requested kinds, covered fingerprint, and completion status. The harness asserts presence and values of all of these.
- **Source**: codebase (step-8-ship.sh, bgjob result-env contract)

## Non-goals (must NOT do)
- Do not change `skills/implement/SKILL.md`. (Stated in issue.)
- Do not wire the adapter into the Step 8 route or activate it — Piece 4 (#6837) owns "activate the combined Step 8 route".
- Do not duplicate Piece 2 logic (materialization, pre-filter, authoring, persistence, HEAD-drift).
- Do not add main-agent inline authoring as a fallback.

## Hard constraints (must preserve)
- Bash 3.2 portability for the new shell script/harness (no associative arrays, namerefs, mapfile, `${var^^}`, `&>>`).
- Symlink/path safety for `$IMPLEMENT_TMPDIR/bgjob` children (mirror step-8-ship.sh / step-8-ci-fixer.sh guards).
- bgjob start/wait/rejoin contract per `skills/shared/bgjob-wait.md`: `BGJOB_STATUS=STARTED` launch row, identical-wait-on-WAIT, DONE requires `BGJOB_RC=0` + required KVs.
- Step slug exactly `implement-step8-assessment`.
