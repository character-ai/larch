## Decision 1: C1a interface for dispatch_panel
- **Question**: Should Python dispatch_panel call run_waterfall() from agents.py directly, or wait for C1a sub-issues to define the full interface?
- **Resolution**: Call run_waterfall() from agents.py (already exists). C1a sub-issues (#4165-4170) will add fuller launcher infrastructure; dispatch_panel.py documents the expected additions. SKILL.md cutover waits until both C1a and C1b complete.
- **Source**: codebase

## Decision 2: prune-nit-findings.sh and reviewer-prune.sh (not in scope)
- **Question**: How should Python review_core call prune-nit-findings.sh and reviewer-prune.sh, which are NOT in C1b scope?
- **Resolution**: Python review_core subprocess-calls the bash scripts directly. This is an acceptable transient state during migration; not a shim. These will be ported in a later issue.
- **Source**: codebase

## Decision 3: aggregate-findings-phrases.inc.bash
- **Question**: Is aggregate-findings-phrases.inc.bash in scope for C1b even though not explicitly listed?
- **Resolution**: Yes — it's a data file sourced by aggregate-findings.sh. Porting aggregate-findings.sh requires porting this file as a Python constant/list.
- **Source**: codebase
