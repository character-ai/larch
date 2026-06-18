### FINDING_2: LIB_COMMON bash parity harness not retired before script deletion
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan deletes `scripts/lib-external-launcher-common.sh` without explicitly retiring `python/test_agents.py` coupling: `LIB_COMMON` path literals, `_bash_classify` / `_bash_startup_lock_acquire` bash subprocess harnesses, and `@pytest.mark.skipif(not LIB_COMMON.is_file())` on parity tests. After deletion, those tests skip instead of failing (silent loss of classify/startup-lock coverage), bash helpers source a missing file, and `make lint-retired-scripts` may flag path literals while CI stays green. The `### UPDATED: python/test_agents.py` section does not spell out removal or Python replacement of this harness before `migrated-scripts.tsv` append.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Require explicit removal or Python replacement of every LIB_COMMON/bash-source parity branch in test_agents.py before migrated-scripts.tsv append; add a fail-closed assertion that no test_agents.py skipif references deleted script paths
  - From Cursor-Pragmatic: make py-test
  - From Cursor-Requirements: Add explicit steps: remove `LIB_COMMON` and all bash-sourced helpers/tests; convert any still-needed assertions to pure-Python fixtures; include `python/test_agents.py` in the pre-delete retired-path `rg` sweep alongside `agent-lint.toml` and `python/checks.py`.


### FINDING_3: failure-diag compose vs append redaction semantics unspecified
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan ports bash `write_failure_diag` section order into `_compose_failure_diag` but does not state whether compose-time redaction stays or matches bash defer-redact-to-append semantics. Bash `write_failure_diag` composes unredacted sections; redaction runs at `append_vendor_failure_diagnostics`. Python `_compose_failure_diag` already redacts before write; expanding compose without an explicit rule can double-redact or shrink `vendor-failure-diagnostics` carriers vs retired bash/drafter behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: State explicitly: either keep bash compose-unredacted + append-only redaction, or document intentional compose-time redaction and add a carrier fixture test that compares staged batch content to a pre-delete bash baseline.


### FINDING_4: drafter CLI verbs must not inherit machine-stdout-only registry test pattern
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Agent drafter registry coverage is aimed at a machine-stdout-only test pattern (`test_design_cli_ports.py` asserts every registry key is in `_MACHINE_STDOUT_KEYS`). Adding `agent launch-codex-drafter` or `agent launch-claude-drafter` to the existing EXPECTED table would also require `_MACHINE_STDOUT_KEYS`, setting `LARCH_QUIET_DISABLE`, and changing quiet routing for launcher KVs and diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add a separate registry-only assertion for the new agent drafter verbs, and keep them out of _MACHINE_STDOUT_KEYS unless a targeted test proves quiet routing is intentionally disabled

