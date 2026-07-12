### OOS_1: Local stall-recovery _session builder is outside the piece-2 migration list
- **Description**: Local stall-recovery _session builder is outside the piece-2 migration list. Scenario: After dispatch migration, test_ship_recovery.py will still hand-write a different session-env contract, leaving duplication and drift risk in the implement cluster.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/implement/test_ship_recovery.py
- **Phase**: design




Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_2: Step 6 entry tests keep a separate local _session helper outside piece 2
- **Description**: Step 6 entry tests keep a separate local _session helper outside piece 2. Scenario: The plan migrates test_implement_dispatch.py but not test_step_6_entry.py or test_run_step_checks.py, so session-env duplication remains in the implement test cluster.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/implement/test_step_6_entry.py
- **Phase**: design




Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_3: Local _write_session_env duplication remains after Piece 2
- **Description**: Local _write_session_env duplication remains after Piece 2. Scenario: Piece 2 migrates the implement and state cluster only. design lifecycle tests still hand-roll session-env.sh, so wire-shape drift can continue outside the migrated surface.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/design/test_design_lifecycle.py:804
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_4: Local design session-env writers remain after Piece 2
- **Description**: Local design session-env writers remain after Piece 2. Scenario: Piece 2 migrates dispatch state closeout and final_report writers but design_lifecycle still hand-builds source-env.sh with divergent defaults
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/design/test_design_lifecycle.py
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

