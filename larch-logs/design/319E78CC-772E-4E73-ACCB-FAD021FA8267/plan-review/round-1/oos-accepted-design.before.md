### OOS_1:
- **Description**: agent-lint.toml exclude rows still name the bash linter/harness paths being deleted. Scenario: After deletion the exclude list keeps stale script paths and comments; low risk because G004 targets skill prose not python/cli.py hooks
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: agent-lint.toml:920-954
- **Phase**: design

### OOS_1:
- **Description**: Deferred relevant-checks case still keys on scripts/lint-readability-preamble.tsv paths only. Scenario: After the manifest moves to python/lint_readability_preamble.tsv, manifest-only edits may not append test-lint-readability-preamble or py-test under relevant-checks until E1 #3690 updates the case; pre-commit always_run still lints but targeted harness/py-test routing is weakened
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/relevant-checks.sh:197-199
- **Phase**: design

### OOS_2:
- **Description**: Per-file mktemp -d fence subdirs (#1426 collision fix) are not mentioned in the plan. Scenario: Extremely rare path pairs differing only by slash vs space could still collide in a naive port
- **Reviewer**: Cursor-dyn-parity-contract
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lint-mermaid-fences.sh:218-223
- **Phase**: design

