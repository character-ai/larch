### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/duplicate_code.py:34-44
- **Concern**: Per-module ingestion list omits astroid module construction before SimilaritiesChecker.process_module. Scenario: Pylint 4 SimilaritiesChecker.process_module takes an astroid nodes.Module and reads node.stream(); tokenize plus process_tokens alone do not produce that node. A literal implementation can call process_module with the wrong type, skip file_state wiring, or diverge from cd python && pylint . discovery.
- **Proposed resolution**: Add an explicit astroid parse step between process_tokens and process_module (or delegate ingestion to pylint's per-file check path with only similarities enabled) and test that process_module receives a real Module for each discovered file.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:241-251
- **Concern**: Mandatory pre-cutover parity gate compares exit codes only, not reportable duplicate clusters. Scenario: The binding goal is findings equivalent to today's R0801, not merely matching pass/fail. Legacy and new runners can both exit 1 while disagreeing on which file pairs/clusters are reportable (especially around close()-equivalent gating and disable attribution), and the merge blocker would still pass
- **Proposed resolution**: Extend the parity gate to compare a normalized reportable-cluster signature for both commands (for example sorted file-pair plus line-span tuples, or a pylint close()-derived digest) and require equality in addition to exit-code equality; keep exit-code check as a fast precheck only

### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:64-70,146-155
- **Concern**: The proposed close-equivalent gating adds custom per-file attribution semantics that Pylint 4.0.5 does not use. Scenario: Pylint filters disabled R0801 lines while building LineSet via line_enabled_callback, then close emits one R0801 per computed cluster. If the runner suppresses or attributes clusters later using custom disabled-file rules, enabled-disabled duplicate pairs can diverge from the legacy pylint pass/fail contract
- **Proposed resolution**: Make LineSet construction through process_tokens/process_module the only per-line disable gate, mirror close/add_message behavior without extra attribution rules, and make disabled-file fixtures assert parity with the legacy pylint command rather than a new enabled-peer rule

### FINDING_4:
- **Reviewer(s)**: Codex-Generic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:14,227-228
- **Concern**: Speed acceptance allows closing the issue with only a linked follow-up instead of meeting the stated ≤90s CI goal. Scenario: If within-runner parallelism still leaves python-lint-duplicate-code above 90s, the plan can file a matrix-sharding follow-up and close while the explicit feature goal remains undelivered
- **Proposed resolution**: Make ≤90s on the real GitHub Actions job a hard acceptance gate for this issue. If the runner misses it, include the needed ci.yaml matrix-sharding change before closing this issue
