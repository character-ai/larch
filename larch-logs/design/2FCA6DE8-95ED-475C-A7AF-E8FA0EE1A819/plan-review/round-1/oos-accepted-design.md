### OOS_1:
- **Description**: Deferred dual-stack keeps bash and Python implementations for the same primitives until E1. Scenario: Contract drift between LARCH_SHIP_PR_IMPL=bash and CLI cutover paths surfaces only on legacy ship or partial cutover
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:9-11
- **Phase**: design

### OOS_2:
- **Description**: Edge cases list `ci-decide` and `check-main-sync` under “always-exit-0-with-status”. Scenario: `ci-decide.sh` exits **1** on invalid argv (`scripts/ci-decide.sh:42-43`, `69-76`, `80-81`); `check-main-sync.sh` exits **1** blocked / **2** probe errors (`scripts/check-main-sync.sh:26-29`, `48-50`)
- **Reviewer**: Cursor-dyn-kv-emission-split
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:183
- **Phase**: design

### OOS_1:
- **Description**: Six new *_cli.py companions for ~40 verbs including single-verb merge domain. Scenario: Six thin companions mirror report_tokens_cli.py but merge_cli.py would wrap only merge pr; gh_cli.py four verbs. Extra modules add registry/import surface without functional gain.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:102-118;python/report_tokens_cli.py
- **Phase**: design

### OOS_2:
- **Description**: [OUT_OF_SCOPE] Separate merge_cli.py for a single merge pr verb adds surface area without functional need. Scenario: A dedicated companion module for one thin wrapper increases migration churn (registry, colocated test file, agent-lint/Makefile pins) beyond B1’s minimum-change goal
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:111-112
- **Phase**: design

### OOS_3:
- **Description**: Duplicate sync-local-main implementations. Scenario: Plan adds public git.sync_local_main for the CLI while rebase._sync_local_main (ship Python path) keeps separate semantics (Stalled vs RESULT KV)
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/git.py:NEW / python/rebase.py:45-69
- **Phase**: design

### OOS_4:
- **Description**: Diagnostic record_failure strings embed bare basenames like git-commit.sh. Scenario: After migration_lint adds bare matching, these prose labels may count as references even when no executable call remains; low risk while ship-pr is frozen until E1
- **Reviewer**: Cursor-dyn-closure-audit
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:789,1401,2621
- **Phase**: design

### OOS_1:
- **Description**: [SCOPE-REDUCTION] NEW merge_cli.py for a single merge verb. Scenario: Playbook already registers modules directly (e.g. migration_lint.main, ship.main); merge has only merge pr
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:110-111
- **Phase**: design

### OOS_1:
- **Description**: [SCOPE-REDUCTION] Six new *_cli.py companions vs in-module CLI entrypoints. Scenario: ship.py registers main inside the domain module; report_tokens_cli.py is the exception for a large pipeline. Six thin wrappers add files and registry indirection without changing runtime behavior
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:110-117
- **Phase**: design

