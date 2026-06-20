## Decision 1: Retired debug/parity harness deletion set
- **Question**: Delete both remaining debug scaffolds, or keep the live one?
- **Resolution**: Delete BOTH `skills/design/scripts/_dbg-validator.sh` and `skills/design/scripts/_dbg5c2.sh` (plus any `.md` siblings), matching the parent #4635 directive to remove `_dbg-*.sh` debug scaffolding. Record deleted paths in `python/migrated-scripts.tsv`.
- **Source**: user

## Decision 2: Scope boundary (Step 6 only)
- **Question**: What is in-scope for this closeout piece vs. the sibling G6 pieces?
- **Resolution**: In-scope: port the Step 6 combined + prelude + cleanup entrypoints to `python/design_lifecycle.py`, register `python/cli.py` rows, delete the three `design-step6*.sh` wrappers + `.md` siblings, port + delete the Step 6 test harness (`test-design-step6.sh`), update `skills/design/SKILL.md`, update `python/migrated-scripts.tsv`, and delete the two debug scaffolds. Out-of-scope: clarify (#4674), terminal/final-summary (#4675), Step 5b (#4676), Step 5c (#4677) — all DONE.
- **Source**: codebase (issue scope + sibling issue states)

## Decision 3: Dependencies landed
- **Question**: Are the blockers (Piece 1, Piece 2, Piece 4) landed?
- **Resolution**: Yes. #4674 (G6.1 clarify), #4675 (G6.2 terminal/final-summary), #4677 (G6.4 step5c) are all CLOSED/DONE. This piece is unblocked. The Step 5c status sidecar contract (`.design-step5c-status.env`: `PLAN_WRITE_OK`, `PUBLISH_OK`, `CLEANUP_ELIGIBLE`, `SESSION_ID`, `STANDALONE_HEAVY_FAILED`) this Step 6 port reads is already produced by the in-process Step 5c port.
- **Source**: codebase (gh issue states)

## Decision 4: Hard constraints to preserve (behavioral parity)
- **Question**: What must not break during the port?
- **Resolution**: Preserve exactly: (a) the combined flow = remove `.pause-save-complete`, run prelude, early-exit if `.pause-save-complete` reappears, else run cleanup; (b) the in-flight guard (`.bg-wait-active` present + missing Step 5c status sidecar → exit 1 with stderr diagnostic); (c) missing-sidecar → skip/preserve, exit 0; (d) `PLAN_WRITE_OK!=true`, `PUBLISH_OK!=true` (when `SESSION_ID` non-empty), `STANDALONE_HEAVY_FAILED==true`, `CLEANUP_ELIGIBLE==false` → preserve `$DESIGN_TMPDIR`; (e) pause-requested → exec `design pause-save`; (f) the **sole deliberate after-pause sentinel placement**: `step-5d` written before pause-check (prelude), but `step-6` written AFTER pause-check and BEFORE `session cleanup-tmpdir` (cleanup); (g) the Step 6 timing mark; (h) all stdout status rows (`STEP6_PRELUDE_STATUS=skipped`, `CLEANUP_STATUS=preserved`).
- **Source**: codebase (wrapper bodies + test-design-step6.sh assertions + SKILL.md pause/resume sentinel table)
