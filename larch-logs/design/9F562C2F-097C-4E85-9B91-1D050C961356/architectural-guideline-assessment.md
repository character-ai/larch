## G-Cfg-1: Mild deviation — duplicate tunable

Plan adds `MAIN_HEALTH_MAX_TRANSIENT_RETRIES: Final = 1` while `CI_MONITOR_TRANSIENT_RERUN_MAX: Final = 1` already exists in `config.py` with the same value.

**Rationale for separate constant**: these control different retry gates. `CI_MONITOR_TRANSIENT_RERUN_MAX` governs per-job rerun attempts inside `ci_monitor.py`. `MAIN_HEALTH_MAX_TRANSIENT_RETRIES` governs the postmerge main-health gate retry cap in `_postmerge_main_health_gate`. They may diverge independently.

**Implementer note**: if the implementer judges G-Cfg-1 compliance more important, reuse `CI_MONITOR_TRANSIENT_RERUN_MAX` (or alias it) in `_postmerge_main_health_gate` instead. Either is acceptable; the decision should be noted in the PR description per the G-Cfg-1 deviate-when clause.
