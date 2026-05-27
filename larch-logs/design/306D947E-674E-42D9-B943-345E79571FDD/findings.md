### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lint-readability-preamble.sh:90-103
- **Concern**: Planned orchestrator-inline failure message uses count, but count is only assigned inside the file-exists branch. Scenario: If the first orchestrator manifest file is missing, set -u can abort on an unbound variable; if a later orchestrator file is missing, the message can reuse a stale count from a previous row
- **Proposed resolution**: Initialize count=0 at the start of each manifest-row loop before the file-exists check, then let missing orchestrator files report found 0 as planned

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-readability-preamble.sh:64-95
- **Concern**: Custom orchestrator-inline failure text uses $count without per-row initialization. Scenario: Under set -u, a missing manifest file (or a row where the case arm never runs) can abort on an unbound count before exit "$missing"; if an earlier row set count, a later missing file can print a stale found N for the wrong path
- **Proposed resolution**: Initialize count=0 at the start of each manifest loop iteration (mirror external-prompt count=0) or use found ${count:-0} only after assigning count inside the orchestrator-inline arm

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lint-readability-preamble.sh:71-103
- **Concern**: Proposed orchestrator-specific failure message can read count when no grep ran. Scenario: If an orchestrator manifest file is missing, set -u can abort on an unset count for the first missing row, or report a stale count after an earlier row, instead of preserving the intended missing=1 lint diagnostics
- **Proposed resolution**: Initialize count=0 before the file-exists guard, or use the generic missing-file message when the file is absent; also render defaults with ${expected_count:-1} and ${count:-0}

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lint-readability-preamble.sh:90-104
- **Concern**: Orchestrator-specific failure message can reference an unset count for missing files. Scenario: If a manifest-listed orchestrator file is deleted or renamed, set -u can abort with an unbound variable instead of the intended greppable lint failure
- **Proposed resolution**: Initialize count before the file-existence branch or keep the generic missing message when the file is absent

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-readability-preamble.sh:71-103
- **Concern**: Planned orchestrator-inline error path can reference count before assignment for missing files. Scenario: If an orchestrator-inline manifest path is absent, the [ -f "$file" ] block is skipped; with set -u, printing found $count in the new specialized error can terminate with an unbound variable instead of reporting the missing directive and continuing lint aggregation
- **Proposed resolution**: Initialize count=0 before the file-existence check for each row, or format the orchestrator-inline error with ${count:-0} while preserving missing=1

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-readability-preamble.sh:64-105
- **Concern**: Plan adds orchestrator-inline stderr that prints found count but does not reset count per manifest row. Scenario: The loop already sets count for external-prompt rows; if a later orchestrator-inline row fails because the file is missing or the case arm is skipped, stderr can report a stale found value from the previous row
- **Proposed resolution**: Mention initializing count=0 at the start of each loop iteration (or at the top of the orchestrator-inline arm) before grep -Ec

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-readability-preamble.sh:41-92
- **Concern**: The plan switches orchestrator-inline enforcement from existence to per-file counts, but the feature asks for per-step or per-block granularity so each specific composition site is protected. Scenario: If one SKILL.md step loses its directive and another step gains a duplicate directive, the total remains 4 and lint still passes while a required per-step readability directive is stale or absent
- **Proposed resolution**: Keep the SIMPLE scope but encode the four SKILL.md directive sites as distinct expected contexts or lightweight per-block anchors instead of only a file-level total; keep one-count rows for single-directive reference files
