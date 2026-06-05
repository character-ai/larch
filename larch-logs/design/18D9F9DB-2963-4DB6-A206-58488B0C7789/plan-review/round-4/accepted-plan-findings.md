### FINDING_1: Duplicate/conflicting restore-mechanism doc bullets (plan + contract)
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-doc-scope-audit
- **Severity**: important
- **Concern**: The plan carries two WI2+WI3 bullets for the `scripts/design-pause-load.md` restore contract that describe the same mechanism inconsistently. One bullet documents a process-substitution `read -d ''` loop; the other (and the WI2 shell bullets) require a guarded `ls-tree` capture into a NUL-terminated temp buffer because process substitution does not surface `ls-tree` failure under `set -euo pipefail`. In `plan.txt`, line 29 omits `-z`, the temp NUL-buffer capture, and the explicit `if ! git ls-tree … >"$enum_tmp"` guard that line 30 and the shell WI2 bullets require. An implementer following only the weaker bullet could document or re-ship an incomplete contract and reintroduce the empty-enumeration / `missing-restored-artifact` masquerade the plan explicitly guards against.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Collapse the duplicate `design-pause-load.md` WI2+WI3 bullets into one paragraph that matches WI2 code: guarded `mktemp` + `if ! git … ls-tree … >"$enum_tmp"` before the `read -d ''` loop, per-path `if ! git show`, no process substitution
  - From Cursor-dyn-doc-scope-audit: Collapse to a single bullet: keep line 30's `-z` + mktemp capture + per-path `if ! git show` wording; delete the redundant line 29 paragraph


