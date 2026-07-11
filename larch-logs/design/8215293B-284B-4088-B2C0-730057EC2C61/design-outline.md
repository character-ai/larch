## Proposed Design Outline

### Goals
- Add a thin bgjob start/wait/rejoin adapter that runs Piece 2's `architectural-assessment run` CLI off the main-agent lane, once per identity (requested kind set plus covered fingerprint).
- Emit and validate canonical result KVs: `BGJOB_RC`, step identity (`implement-step8-assessment`), requested kinds, covered fingerprint, and completion status.
- Add a harness that covers fresh start, live rejoin, completed rejoin, deterministic skip, authored success, stale rejection, timeout fallback, invalid-output fallback, and required KVs.

### Non-goals
- Do not change `skills/implement/SKILL.md`. Do not activate the Step 8 route (Piece 4, #6837).
- Do not duplicate Piece 2 logic (materialization, pre-filter, authoring, persistence, HEAD-drift).
- No main-agent inline authoring as a fallback.

### Approach sketch
- Mirror the `step-8-ship.sh` adapter shape: check registry liveness, check completed-rejoin, else clear stale envelope and `bgjob start` a child that delegates to `architectural-assessment run`.
- Identity gate: compute one covered-fingerprint digest over the requested kind set and each kind's materialization identity (`HEAD_SHA`, `BASE_REF`, `DIFF_FINGERPRINT`). Rejoin live or completed work only on an exact kind-set and digest match.
- On bgjob timeout (exit 124) or Piece 2 invalid/failed output, re-launch once, then fail closed via a fail-closed result KV.
- Result env carries `STEP`, `BGJOB_RC`, `REQUESTED_KINDS`, `COVERED_FINGERPRINT`, `ASSESSMENT_STATUS`, and per-kind completion.
- The `.md` pair documents the step contract and the harness scenarios. Keep shell Bash 3.2-safe with the same symlink and path guards as `step-8-ship.sh`.

### Surfaces in scope
- skills/implement/scripts/step-8-assessment.sh
- skills/implement/scripts/step-8-assessment.md
- skills/implement/scripts/test-step-8-assessment.sh
- skills/implement/scripts/test-step-8-assessment.md

### Open questions
- None. Scope is pinned by parent #6801 and the Step 1c answers.
