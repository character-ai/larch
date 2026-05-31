### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/write-session-env.sh:32,scripts/implement-bootstrap.sh:563-586
- **Concern**: Sourcing write-session-env.sh applies top-level set -euo to the bootstrap shell. Scenario: implement-bootstrap intentionally runs set -uo without errexit; sourcing the writer mid resume enables -e and can abort best-effort Step 0 on benign helper failures
- **Proposed resolution**: Define emit_plugin_root_env before the guard; move set -euo pipefail lib-quiet init and argument parsing inside if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; or run . write-session-env.sh and emit_plugin_root_env in a subshell so errexit does not leak

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/write-session-env.sh (proposed)
- **Concern**: BASH_SOURCE guard scope underspecified for sourced resume path. Scenario: Sourcing with set -e or exit outside the guard enables errexit in implement-bootstrap or aborts resume on missing --output
- **Proposed resolution**: Keep set -euo pipefail lib-quiet init argument parsing validation and main write inside the BASH_SOURCE guard; only emit_plugin_root_env outside

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/write-session-env.sh (proposed emit_plugin_root_env)
- **Concern**: No return-vs-exit contract when called from sourced bootstrap. Scenario: exit from emit_plugin_root_env kills implement-bootstrap during --resume-plan-tail
- **Proposed resolution**: Use return 0 on skip/invalid value; reserve exit for argv0 execution path only

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-timing-rehydration.sh:128-132
- **Concern**: skills/implement/SKILL.md:105-108,307-311,466-469. Scenario: Plan assertion (b) still counts awk via grep -Fxc of a standalone line ` CLAUDE_PLUGIN_ROOT=$(awk`, but pre-bootstrap fences use a single compound line starting with `[` and embed `CLAUDE_PLUGIN_ROOT=$(awk` after `&&`
- **Proposed resolution**: After SKILL migration, awk-extract grep count is 0 (or not 3); `make test-implement-timing-rehydration` fails or the parity check is retired without a replacement that matches the new shape In the same PR, change assertion (b) to count lines containing `CLAUDE_PLUGIN_ROOT=$(awk` and `LARCH_CLAUDE_PLUGIN_ROOT=` (or match the exact compound-line template), and align `test-implement-timing-rehydration.md` invariant 4 / Invariant C with that detector

### OOS_1:
- **Description**: SECURITY.md not in plan file list. Scenario: New sourceable plugin-root.env contradicts awk-only consumer wording
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: architecture
- **Location**: SECURITY.md:234
- **Phase**: design
