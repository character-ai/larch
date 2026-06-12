### OOS_1:
- **Description**: Parametrized env-ladder coverage over every tuple plus a full port of generic `env_rate()` tests is disproportionate for a constants correction.. Scenario: Rate default changes already have a single snapshot test and targeted override tests; exhaustive ladder parametrization adds maintenance without new failure modes on the repricing path.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_report_tokens_cost.py:501-520
- **Phase**: design

### OOS_1:
- **Description**: Bash-only `ship-pr.sh` recovery ingestion does not help operators on the default Python ship driver. Scenario: When `LARCH_SHIP_PR_IMPL` is unset, `python/ship.py` owns CI fix/recovery; patching bash `run_recovery_waterfall` alone leaves the common path incomplete (see in-scope Python gap above).
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:355-370
- **Phase**: design

### OOS_2:
- **Description**: Parametrized env-ladder test matrix duplicates existing `env_rate()` coverage. Scenario: Exhaustive per-alias parametrized tests across every ladder tuple add harness bulk without new failure modes beyond alias precedence already covered in `python/test_report_tokens_cost.py` / ported `env_rate()` tests.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: plan.txt:501-511
- **Phase**: design

