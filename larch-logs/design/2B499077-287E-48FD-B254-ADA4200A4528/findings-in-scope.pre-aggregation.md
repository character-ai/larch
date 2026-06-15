### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:543-598
- **Concern**: [SCOPE-REDUCTION] Collapsing the foreground `step-5-entry.sh` fence and the immediate-background `review-and-fix step5` fence into one background `step-5-review.sh` call defers the Step 5 banner until `<task-notification>`. Scenario: The plan removes orchestrator-side banner printing and emits the banner only from wrapper stdout inside an immediate-background fence. `/implement` anti-halt and `orchestrator-never.md` forbid reading child output before notification, so the operator loses the long-running Step 5 start breadcrumb for the whole review loop. That regresses the current foreground-entry contract and progress-reporting step-start visibility.
- **Proposed resolution**: Keep one Bash call but restore operator-visible banner timing: have the orchestrator print the same byte-stable banner line immediately before launching `step-5-review.sh` (inline the existing cap precedence in SKILL prose), or document an explicit immediate-background carve-out that permits emitting the wrapper's leading banner before the yield.

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:588-598
- **Concern**: Moving the Step 5 banner into the immediate-background wrapper defers the only scripted-loop start breadcrumb until task-notification. Scenario: The plan removes orchestrator "Print once before" and prints the banner inside step-5-review.sh stdout. The scripted loop runs with run_in_background and waits for task-notification before parsing stdout. Operators see no Step 5 start line for the full review duration (often hours), breaking skills/shared/progress-reporting.md step-start visibility and the acceptance "banner output stays byte-compatible" timing contract
- **Proposed resolution**: Preserve operator-visible banner at launch: keep orchestrator-side banner emission before the background fence (Read session-env for LARCH_DYNAMIC_ARCHETYPES_MAX with the same precedence), or have the wrapper write a synchronous sidecar and SKILL instruct reading/printing it on the launch ack before END TURN; do not rely on full task stdout as the sole banner channel

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:543-549
- **Concern**: Removing the top-level step-5-entry.sh fence drops Step 5 telemetry-mark on the --self-review path. Scenario: The plan deletes the unconditional entry fence and only calls step-5-review.sh inside the scripted loop. Self-review skips that loop but today still gets timing telemetry-mark --label "Step 5 — code review" from step-5-entry.sh. Self-review runs lose that mark and timing-ledger coverage regresses.
- **Proposed resolution**: Add a self-review-only foreground fence before the self-review banner that runs the same telemetry-mark (e.g. bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py timing telemetry-mark --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 5 — code review"), or extract a minimal shared mark helper both paths call.

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-fence-shape.sh:37
- **Concern**: Plan omits updating EXPECTED_NEW after removing one SKILL.md Bash fence. Scenario: Removing the step-5-entry.sh fence and folding review-and-fix into step-5-review.sh reduces new-shape fence count from 31 to 30. test-implement-fence-shape.sh hard-fails on mismatch (make test-harnesses-3 / make lint). Acceptance cites structure harnesses staying green but the plan testing strategy does not list this harness.
- **Proposed resolution**: Update scripts/test-implement-fence-shape.sh EXPECTED_NEW to 30, or add the self-review telemetry fence above so the net fence count stays 31.

### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-step5-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-entry.sh:44-50
- **Concern**: Planned cap logic copies session-env-first precedence but review dispatch uses process-env-first. Scenario: `step-5-review.sh` is specified to copy `step-5-entry.sh` cap resolution (session-env awk, then process `LARCH_DYNAMIC_ARCHETYPES_MAX`, then default `3`), while `review-and-fix step5` resolves the cap in `_dynamic_archetypes` with process env before session-env (`python/review_and_fix.py:1497-1499`). When those sources disagree the banner can show cap N while the review loop runs (or stalls on) cap M; e.g. session-env `2` plus process `9` yields banner `cap=2` then `STEP5_REVIEW_STATUS=stall` from dispatch
- **Proposed resolution**: In `step-5-review.sh`, mirror `_dynamic_archetypes` precedence (process env, then session-env, then default `3`) or call a shared resolver; do not copy session-first `step-5-entry.sh` order if the banner must match dispatch

### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-retirement-cleanliness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:543-545
- **Concern**: Removing the unconditional step-5-entry.sh fence drops Step 5 telemetry-mark for --self-review runs. Scenario: Today skills/implement/SKILL.md:543-545 runs step-5-entry.sh before the self-review vs scripted branch. That script calls timing telemetry-mark (skills/implement/scripts/step-5-entry.sh:42), which writes both token and timing ledger marks. Self-review never calls review-and-fix step5, so it will not get the Python timing mark in python/review_and_fix.py:1931. Deleting the top fence with no self-review replacement removes Step 5 telemetry for --self-review runs.
- **Proposed resolution**: Add a self-review-only telemetry fence under ### Self-review mode (for example bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py timing telemetry-mark --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 5 — code review") before the inline review steps. Revise the Edge cases bullet that claims self-review is unaffected.

