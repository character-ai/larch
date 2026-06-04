### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/upgrade-larch/SKILL.md:21
- **Concern**: Exported skill Step 2 still treats any "Already at latest stable larch release" line as no reinstall and no restart. Scenario: After RC2, cone-drift reconcile prints an already-latest prefix then uninstalls/reinstalls and ends with the normal upgrade-complete restart guidance; following Step 2 would mis-report success to the operator
- **Proposed resolution**: Add skills/upgrade-larch/SKILL.md to the change list: early-exit/no-restart only when latest and cone match; reconcile-on-drift needs reinstall plus restart messaging

### FINDING_2:
- **Reviewer(s)**: Codex-Arch, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/sessionstart-health.sh:31-54
- **Concern**: The proposed SessionStart drift probe expands HOME under set -u without a missing-HOME guard. Scenario: SessionStart has an always-exit-0 contract; if the hook environment has jq and git but no HOME, MARKETPLACE_CLONE="$HOME/..." aborts before the final exit 0
- **Proposed resolution**: Use a local home_dir=${HOME:-} guard and skip the drift probe when empty; keep fixture HOME injection for drift cases without relying on HOME being globally present

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/sessionstart-health.sh:54-114 (proposed drift probe)
- **Concern**: Drift probe lacks the failure guards that marketplace_sparse_cone_matches uses under set -euo pipefail. Scenario: When git sparse-checkout list fails or returns empty output the hook treats empty configured as a mismatch and append_msg a drift warning—or an unguarded source/git step aborts before exit 0 violating the SessionStart non-blocking contract
- **Proposed resolution**: Mirror marketplace_sparse_cone_matches: wrap the whole probe in a set +e block or subshell; use source ... || true; append git ... || true; skip silently when configured is empty ([ -n "$configured" ] before comparing)

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/lib-sparse-dirs.sh:1
- **Concern**: The new sourced-only .sh file is specified as having no shebang but the plan does not add a ShellCheck shell directive.. Scenario: The repo's shellcheck hook scans shell files with shellcheck -x; a no-shebang .sh without `# shellcheck shell=bash` triggers SC2148 and can fail lint before the behavioral tests run.
- **Proposed resolution**: Start `scripts/lib-sparse-dirs.sh` with `# shellcheck shell=bash` and list that invariant in `scripts/lib-sparse-dirs.md`, while keeping the file non-executable and sourced-only.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/sessionstart-health.sh:17-160
- **Concern**: Drift probe not isolated from errexit under set -euo pipefail. Scenario: A failing source/git/compare in the new probe exits non-zero before the hook’s exit 0, breaking SessionStart’s non-blocking contract
- **Proposed resolution**: Wrap the drift probe in a best-effort block (set +e or subshell) and use source ... || true plus guarded git/compare, mirroring the lib-resolve source at line 127

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/upgrade-larch/SKILL.md:21-22
- **Concern**: Plan omits SKILL.md though upgrade-larch.md edit-in-sync requires it. Scenario: After RC2, same-version cone reconcile reinstalls and updates the sparse cone/cache but Step 2 still treats only the Already at latest line as no-restart; reconcile messaging is undocumented so operators may skip restart and keep a session without new allowlist dirs (e.g. python/)
- **Proposed resolution**: Add skills/upgrade-larch/SKILL.md to Files to modify: update Step 2 for early-exit only when latest and cone match; document the reconcile advisory and require restart after a reconcile reinstall even when the version string is unchanged

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:106; Makefile:191-192
- **Concern**: Testing strategy names non-existent make test-sessionstart-health target. Scenario: The implementer following the plan will hit No rule to make target test-sessionstart-health or skip the SessionStart drift regression target
- **Proposed resolution**: Replace make test-sessionstart-health with existing make test-sessionstart; do not add a new alias unless needed elsewhere
