### FINDING_1: Step 5c shared validator handler can still use bare composed-plan validation
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Edge, Cursor-Requirements, Cursor-dyn-cross-doc-drift
- **Severity**: important
- **Concern**: The generic shared validator-failure Fix/Override bullets still allow or prescribe bare `ACTION=VALIDATE_PLAN_COMMANDS` on `composed-plan.md` and generic success continuation. At the Step 5c `design-publish.sh` site, that can bypass the folded redact/publish/rename driver path, skip Gate C completion, or avoid the intended rc-4 retry loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Innovation: Restrict generic bullets to `plan.txt` sites only, or add explicit precedence: at `design Step 5c`, Fix/Override/Cancel follow only the `--site design Step 5c` bullets (`design-publish.sh` re-capture; Override uses `--skip-validate`); update **Cancel** Step 5c text to items 3–5 gating instead of listing redact/publish steps that the driver now owns
  - From Cursor-Edge: Rewrite generic Fix/Override to plan.txt-only or subordinate them to the Step 5c site branch that re-captures design-publish.sh
  - From Cursor-Requirements: Retarget the shared section trigger to VALIDATE_STATUS=defects-found (plan.txt via postplan/inline capture; Step 5c via design-publish exit 4). Limit the generic Fix-and-retry bullet to plan.txt; defer composed-plan.md solely to the --site design Step 5c branch (design-publish re-capture / --skip-validate)
  - From Cursor-dyn-cross-doc-drift: Scope generic Fix/Override to plan.txt only, or add explicit supersession prose (“When --site is design Step 5c, follow the site branch; do not use the generic Fix/Override bullets”) and update Override for Step 5c to re-capture design-publish.sh --skip-validate instead of “continue surrounding success path”

### FINDING_2: Step 5c parser may abort before shared handler on rc 4 without result env
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Cursor-Pragmatic, Codex-Requirements, Cursor-dyn-retry-state-invariant
- **Severity**: important
- **Concern**: The Step 5c parse-or-abort guard still appears to treat missing or unreadable `.design-publish-result.env` as fatal for `design-publish.sh` exit code 4. If defects are reported through stdout `VALIDATE_*` fallback but the result env write fails, `/design` can abort before routing to the shared Fix/Override/Cancel handler.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Revise the proposed Step 5c parse fence so rc 4 also accepts stdout fallback when the result env is absent or unreadable, then route parsed VALIDATE_* values to the shared validator-failure handler instead of aborting.
  - From Cursor-Edge: Allow stdout-only parse when _publish_rc is 4 (mirror rc=3) and add a structure-test pin
  - From Cursor-Pragmatic: Extend the guard to also skip abort when _publish_rc is 4 (mirror rc 3 stdout-authoritative handling), or require _publish_parse_ok once stdout contains VALIDATE_STATUS=defects-found
  - From Codex-Requirements: In the Step 5c proposed parser changes, explicitly allow stdout fallback for _publish_rc=4 when VALIDATE_STATUS=defects-found is parsed, before the missing/unreadable result-env abort. Add a narrow structural/test pin for this rc-4 stdout-fallback case.
  - From Cursor-dyn-retry-state-invariant: Mirror the rc 3 carve-out: change the guard to also allow `_publish_rc=4` when `_publish_out` carries `VALIDATE_*` (or drop the abort for rc 4 entirely). Pin in `scripts/test-design-structure.sh`.

### FINDING_3: Removing legacy flags may break existing callers instead of making them no-op
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan removes documented compatibility flags such as `--review-budget full` and `--force-validate`. Existing callers or resumed instructions may still pass those flags and would fail with unknown-option errors, even though unconditional validation does not require breaking those call sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Keep the parsers accepting these legacy flags as ignored/no-op in this PR; remove only the gating/reader behavior and defer flag/schema deletion to a separate compatibility cleanup
