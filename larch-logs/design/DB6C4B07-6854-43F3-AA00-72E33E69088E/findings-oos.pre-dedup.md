### OOS_1: Plan cites `test_step2b_postplan_pause_requested_exits_11` but the repo test is `test_step2b_postplan_rc_11_raises_system_exit`
- **Description**: Plan cites `test_step2b_postplan_pause_requested_exits_11` but the repo test is `test_step2b_postplan_rc_11_raises_system_exit`. Scenario: Implementer grep misses the real direct `_shared_step2b_postplan_body` test and may skip updating it for the required `design_tmpdir=` argument
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_design_lifecycle.py:1486
- **Phase**: design



### OOS_2: Monolithic Ctx carries design implement and agent keys in one type
- **Description**: Monolithic Ctx carries design implement and agent keys in one type. Scenario: Hotspot boundaries only need small per-surface snapshots; one large type encourages cross-module coupling in later tranches
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/ctx.py:26-66
- **Phase**: design



### OOS_3: [SCOPE-REDUCTION] Plan adds `ENV_LOGNAME` with no converted read site in this tranche
- **Description**: [SCOPE-REDUCTION] Plan adds `ENV_LOGNAME` with no converted read site in this tranche. Scenario: `LOGNAME` is only read in unconverted `validate_plan_commands` subprocess env assembly (`plan_quality.py` ~943); adding the constant expands config surface without advancing the hotspot `Ctx` adoption goal
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/config.py:97-101
- **Phase**: design



