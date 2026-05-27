### FINDING_1: Orchestrator-inline error path can read stale or unset count
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The orchestrator-inline lint failure message prints `count`, but `count` is not initialized for each manifest row before file-existence checks. Missing files, skipped case arms, or prior loop values can cause `set -u` aborts or stale “found N” diagnostics instead of the intended lint failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Initialize count=0 at the start of each manifest-row loop before the file-exists check, then let missing orchestrator files report found 0 as planned
  - From Cursor-Edge: Initialize count=0 at the start of each manifest loop iteration (mirror external-prompt count=0) or use found ${count:-0} only after assigning count inside the orchestrator-inline arm
  - From Codex-Edge: Initialize count=0 before the file-exists guard, or use the generic missing-file message when the file is absent; also render defaults with ${expected_count:-1} and ${count:-0}
  - From Codex-Innovation: Initialize count before the file-existence branch or keep the generic missing message when the file is absent
  - From Codex-Pragmatic: Initialize count=0 before the file-existence check for each row, or format the orchestrator-inline error with ${count:-0} while preserving missing=1
  - From Cursor-Requirements: Mention initializing count=0 at the start of each loop iteration (or at the top of the orchestrator-inline arm) before grep -Ec

### FINDING_2: File-level counts can miss per-step directive regressions
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Switching orchestrator-inline enforcement to a file-level count does not protect each required per-step or per-block composition site. A removed directive in one step and a duplicate in another could preserve the expected total while still leaving a required site stale or absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Keep the SIMPLE scope but encode the four SKILL.md directive sites as distinct expected contexts or lightweight per-block anchors instead of only a file-level total; keep one-count rows for single-directive reference files
