### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-load.md:33-37
- **Concern**: Plan lists two conflicting WI2 doc bullets for the restore mechanism — the first tells the contract to document a process-substitution `read -d ''` loop; the second (and WI2 code) require a guarded `ls-tree` capture to a NUL temp buffer because process substitution does not surface `ls-tree` failure under `set -euo pipefail`. Scenario: An implementer following the first bullet documents the rejected pattern; a later maintainer may reintroduce the empty-enumeration / `missing-restored-artifact` masquerade the plan explicitly guards against
- **Proposed resolution**: Collapse the duplicate `design-pause-load.md` WI2+WI3 bullets into one paragraph that matches WI2 code: guarded `mktemp` + `if ! git … ls-tree … >"$enum_tmp"` before the `read -d ''` loop, per-path `if ! git show`, no process substitution

### FINDING_2:
- **Reviewer(s)**: Cursor-dyn-doc-scope-audit
- **Severity**: nit
- **Focus area**: correctness
- **Location**: plan.txt:29-30
- **Concern**: Duplicate WI2+WI3 bullets for `scripts/design-pause-load.md` contract update. Scenario: Line 29 omits `-z`, temp NUL-buffer capture, and explicit `if ! git ls-tree … >"$enum_tmp"` guard that line 30 and the shell WI2 bullets require; an implementer following only line 29 could ship an incomplete contract paragraph
- **Proposed resolution**: Collapse to a single bullet: keep line 30’s `-z` + mktemp capture + per-path `if ! git show` wording; delete the redundant line 29 paragraph

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-marker-refactor-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-load.sh:34-43,296-306
- **Concern**: Post-success clear_pause_marker lacks explicit set -e guard in plan. Scenario: WI3 drops the internal `|| true` at line 42 and adds a bare success-path call; under `set -euo pipefail` a failed `named-block-write.sh --delete` aborts before `emit_kv LOAD_OK true`, so design-route.sh sees `_pause_rc != 0` and adds `design-pause-load-failed` (skills/design/scripts/design-route.sh:314-316) instead of `LOAD_OK=true` plus `WARN=marker-delete-failed`
- **Proposed resolution**: Spell out the success-path snippet: `if ! clear_pause_marker; then` set/append `WARN_VALUE` to `marker-delete-failed` without clobbering an existing `body-drift`; `fi` then emit `LOAD_OK=true` — same explicit `if !` style as WI2 git guards
