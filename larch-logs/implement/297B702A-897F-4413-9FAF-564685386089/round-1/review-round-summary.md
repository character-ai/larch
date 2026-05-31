# Review Round 1

- Mode: `diff`
- 7 accepted, 6 rejected (6 exonerated)

## Accepted Findings

### FINDING_1: code-quality: scripts/test-ship-pr.sh:6042-6049
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] OOS errexit probes export CLAUDE_PLUGIN_ROOT after source so PLUGIN_ROOT is frozen to REPO_ROOT and the no-op gate stub under tmp/plugin is never used. Probes exercise the real oos-disposition-gate.sh and repo git context; errexit assertions can pass while violating plan hermeticity and may flake if the real gate behavior changes. Export CLAUDE_PLUGIN_ROOT (or set PLUGIN_ROOT) before sourcing ship-pr.sh so gate_script resolves to the stub.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: scripts/ship-pr.md:67
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New Errexit invariant section documents baseline as set +uo pipefail instead of set -uo pipefail. A maintainer follows ship-pr.md and believes nounset/pipefail are disabled or errexit is part of the baseline; future edits could re-break CI capture or leak errexit. Replace with set -uo pipefail to match scripts/ship-pr.sh:4.
- **Suggested revision**: Address the concern above.


### FINDING_18: code-quality: scripts/test-ship-pr.sh:470-472
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Section inventory comment omits errexit though the section runs in default full test-ship-pr. Contributors may not discover errexit tests when debugging section failures. Update the comment to list errexit.
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: scripts/ship-pr.md:67
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] New Errexit invariant section documents baseline as `set +uo pipefail` but ship-pr.sh uses `set -uo pipefail` at line 4. A maintainer copying the documented set line would disable nounset/pipefail instead of matching production entrypoint behavior. Replace with `set -uo pipefail` and clarify errexit is intentionally off (no `set -e`).
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: scripts/ship-pr.md:67
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Errexit invariant documents set +uo pipefail but ship-pr.sh uses set -uo pipefail without -e. Maintainers may misread the script baseline and reintroduce wrong set options when adding gate blocks. Say set -uo pipefail and note errexit is intentionally off (no set -e).
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/ship-pr.md:67
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] New errexit section says ship-pr runs with set +uo pipefail; script actually uses set -uo pipefail (u and pipefail on, errexit off). Maintainer misreads baseline shell options or copies wrong set line when editing ship-pr.sh. State set -uo pipefail with errexit off (set +e), matching scripts/ship-pr.sh:4-7.
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: scripts/ship-pr.md:67
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Errexit invariant documents set +uo pipefail instead of set -uo pipefail. Maintainers may believe nounset/pipefail are disabled when debugging errexit leaks. Change +uo to -uo to match scripts/ship-pr.sh:4.
- **Suggested revision**: Address the concern above.


