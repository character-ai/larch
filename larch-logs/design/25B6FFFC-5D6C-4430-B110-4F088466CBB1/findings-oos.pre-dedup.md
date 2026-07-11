### OOS_1: Harden _artifact_present / is_pr_mutation_gate_relevant symlink gate detection
- **Description**: Harden _artifact_present / is_pr_mutation_gate_relevant symlink gate detection. Scenario: _artifact_present treats symlinks as present, so a planted symlink under plan-coverage.json or scope-disposition.json can mark the PR mutation gate relevant and route into consumers before full artifact validation. Real TOCTOU risk, but outside the plan's stated hardening surface.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: security
- **Location**: python/larch/implement/scope_disposition.py:143-164
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Consolidate commit-route coverage relay into scope_disposition
- **Description**: [OUT_OF_SCOPE] Consolidate commit-route coverage relay into scope_disposition. Scenario: _relay_scope_coverage duplicates advisory fallback and KV emission logic that validate_disposition_for_ship already owns; two edited paths increase the chance commit routing and ship validation diverge after hardening
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/dispatch_commit_route.py:59-104
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] Reuse existing no-follow read helper before adding generic trusted-I/O primitives
- **Description**: [OUT_OF_SCOPE] Reuse existing no-follow read helper before adding generic trusted-I/O primitives. Scenario: architectural_guidelines already implements _read_regular_text_no_follow; the plan adds a second generic trusted-read layer in io.py plus snapshot-local copies, increasing surface area for a coverage-only fix
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/io.py:1-120
- **Phase**: design



### OOS_4: [OUT_OF_SCOPE] The plan hardens disposition reads but leaves disposition creation on the predictable default atomic temporary path
- **Description**: [OUT_OF_SCOPE] The plan hardens disposition reads but leaves disposition creation on the predictable default atomic temporary path. Scenario: A same-UID process can plant `scope-disposition.json.tmp` before `record_disposition` runs. The current default `atomic_write` path can follow that symlink and overwrite an unrelated file, although later trusted loading may reject the resulting disposition state.
- **Reviewer**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/implement/scope_disposition.py:782-824
- **Phase**: design



