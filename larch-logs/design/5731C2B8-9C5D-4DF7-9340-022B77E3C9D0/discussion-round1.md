## Decision 1: Assessment bgjob integration model
- **Question**: Should SKILL.md's Step 8 `assessments` branch invoke `step-8-assessment.sh` as one blocking foreground fence (adapter owns bgjob start, the wait loop, validation, and one retry), or drive an explicit main-agent bgjob start/wait pair?
- **Resolution**: Blocking foreground fence. SKILL.md invokes `step-8-assessment.sh` (via the implement-run launcher) as a single blocking fence; the adapter owns bgjob start, the internal `bgjob wait --max-wait-s 270` loop (repeat on WAIT), terminal validation, and the single retry. On a Bash-tool timeout the main agent re-invokes the identical fence and the adapter live-rejoins the running job. After terminal KVs, validate `BGJOB_RC=0` + `STEP=implement-step8-assessment` + `ASSESSMENT_COVERED_FINGERPRINT` + `ASSESSMENT_REQUESTED_KINDS` + `ASSESSMENT_STATUS=complete`, then relaunch `step-8-ship.sh` exactly once.
- **Source**: user

## Decision 2: Adapter and Python drivers stay out of scope
- **Question**: Does piece 4 change `step-8-assessment.sh` / `step-8-assessment.md` or the Python `ship route-exit` / `architectural-assessment` drivers?
- **Resolution**: No. The scope is exactly SKILL.md, the two `architectural-*-present.md` reference files, `ship-pr-exit-matrix.md`, the three named test files, and SECURITY.md. The adapter and Python routers are already built (pieces 1-3) and must not change.
- **Source**: codebase (issue scope list; `ship.py:649` emits only the combined `architectural-assessments` reason)

## Decision 3: Back-compat single-kind routes are dormant legacy aliases
- **Question**: How do the back-compat `invariants-assessment` / `guidelines-assessment` routes reach the combined-only adapter (`NEXT_ACTION must be assessments`)?
- **Resolution**: They do not fire from current Python (`ship.py` emits only the combined `architectural-assessments` reason; `dispatch_ship.py` still maps the single-kind reasons for one release of back-compat). Piece 4 keeps the two back-compat SKILL.md branches as thin legacy aliases that delegate to the same adapter, pinned by tests, and documents them as dormant. No adapter or Python change is needed to support them.
- **Source**: codebase (`python/larch/implement/ship.py:649`, `python/larch/implement/dispatch_ship.py:241-245`)
