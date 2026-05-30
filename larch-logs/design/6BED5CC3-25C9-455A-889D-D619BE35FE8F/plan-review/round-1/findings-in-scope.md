### FINDING_1: Duplicate Gate A/B regression pins in `test-design-structure.sh`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-regression-anchor-validity
- **Severity**: important
- **Concern**: The proposed UPDATED block at `scripts/test-design-structure.sh:397-423` adds Gate A/B trailer-guard pins that largely duplicate existing (3175) grep assertions (e.g. `gate-b-dedup-plan.sh`, `--snapshot-trailers`, `--dedup` at 399-402, approval-gates hook at 397-398). Implementing a new `contains()`-style block would re-test SKILL.md anchors already enforced elsewhere, adding substantial diff with little new signal versus tightening weaker snapshot substring checks at 403-408.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Drop the new Check N block; at most tighten 403-408 to grep literal --snapshot-trailers and --dedup in APPROVAL_MD and DISCUSSION_MD instead of adding parallel SKILL pins
  - From Cursor-Innovation: Drop UPDATED scripts/test-design-structure.sh from the plan; keep Claim #1 as already resolved via existing pins and test-gate-b-dedup-plan.sh
  - From Cursor-dyn-regression-anchor-validity: Revise the plan to extend the existing (3175) block only: add literal --snapshot-trailers and --dedup pins for $APPROVAL_MD and $DISCUSSION_MD (and gate-b-dedup-plan.sh in discussion-rounds.md if desired); skip new SKILL.md contains for tokens already covered at 399-402

### FINDING_2: Invoke-only harness must be executable
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The invoke-only harness for `skills/design/scripts/test-trailer-awk.sh` (proposed; wired like existing `test-trailer-has-any.sh` adapters at `skills/design/scripts/test-trailer-helpers.sh:36-41`) must be executable. Sibling `test-trailer-*.sh` scripts are `+x` today; a new file defaulting to `644` yields `Permission denied` and `make test-trailer-helpers` fails closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Require `chmod +x` on `test-trailer-awk.sh` (match sibling `test-trailer-*.sh`) or invoke via `bash "$SCRIPT_DIR/test-trailer-awk.sh"`.

### FINDING_3: `has_key` exit-1 cases under `set -euo pipefail` not specified
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `has_key` exit-1 behavior under `set -euo pipefail` is not specified for the new harness (`plan.txt:69-73`). New `test-trailer-awk.sh` can abort on the first expected `has_key` failure before assertions run, so the harness fails to execute or falsely fails under `set -e`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Mirror `test-trailer-helpers.sh` / `test-gate-b-dedup-plan.sh`: wrap each expected non-zero `awk`/`has_key` probe in `set +e` … `set -e` or `if ! awk …`; document that pattern in `test-trailer-awk.md`
