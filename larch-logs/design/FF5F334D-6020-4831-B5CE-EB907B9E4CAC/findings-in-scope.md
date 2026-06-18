### FINDING_1: Missing astroid Module before `process_module`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Per-module ingestion omits astroid module construction before `SimilaritiesChecker.process_module`. Pylint 4 `SimilaritiesChecker.process_module` expects an astroid `nodes.Module` and reads `node.stream()`; tokenize plus `process_tokens` alone do not produce that node. A literal implementation can call `process_module` with the wrong type, skip `file_state` wiring, or diverge from `cd python && pylint .` discovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit astroid parse step between `process_tokens` and `process_module` (or delegate ingestion to pylint's per-file check path with only similarities enabled) and test that `process_module` receives a real `Module` for each discovered file.

### FINDING_2: Parity gate checks exit code only, not reportable clusters
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The mandatory pre-cutover parity gate compares exit codes only, not reportable duplicate clusters. The binding goal is findings equivalent to today's R0801, not merely matching pass/fail. Legacy and new runners can both exit 1 while disagreeing on which file pairs/clusters are reportable (especially around close()-equivalent gating and disable attribution), and the merge blocker would still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the parity gate to compare a normalized reportable-cluster signature for both commands (for example sorted file-pair plus line-span tuples, or a pylint close()-derived digest) and require equality in addition to exit-code equality; keep exit-code check as a fast precheck only
  - From Cursor-Pragmatic: Extend the parity gate to compare a normalized reportable-cluster signature for both commands (for example sorted file-pair plus line-span tuples, or a pylint close()-derived digest) and require equality in addition to exit-code equality; keep exit-code check as a fast precheck only

### FINDING_3: Custom close-equivalent gating diverges from Pylint disable semantics
- **Reviewer(s)**: Codex-Generic
- **Severity**: blocking
- **Concern**: The proposed close-equivalent gating adds custom per-file attribution semantics that Pylint 4.0.5 does not use. Pylint filters disabled R0801 lines while building `LineSet` via `line_enabled_callback`, then `close` emits one R0801 per computed cluster. If the runner suppresses or attributes clusters later using custom disabled-file rules, enabled-disabled duplicate pairs can diverge from the legacy pylint pass/fail contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Make LineSet construction through `process_tokens`/`process_module` the only per-line disable gate, mirror `close`/`add_message` behavior without extra attribution rules, and make disabled-file fixtures assert parity with the legacy pylint command rather than a new enabled-peer rule

### FINDING_4: Speed goal can be deferred via follow-up instead of hard gate
- **Reviewer(s)**: Codex-Generic
- **Severity**: blocking
- **Concern**: Speed acceptance allows closing the issue with only a linked follow-up instead of meeting the stated ≤90s CI goal. If within-runner parallelism still leaves `python-lint-duplicate-code` above 90s, the plan can file a matrix-sharding follow-up and close while the explicit feature goal remains undelivered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Make ≤90s on the real GitHub Actions job a hard acceptance gate for this issue. If the runner misses it, include the needed `ci.yaml` matrix-sharding change before closing this issue
