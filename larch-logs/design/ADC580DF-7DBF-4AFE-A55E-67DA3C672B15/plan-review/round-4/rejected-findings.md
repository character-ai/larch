### [Plan Review] FINDING_1

### FINDING_1: Step 5c shared validator handler can still use bare composed-plan validation
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Edge, Cursor-Requirements, Cursor-dyn-cross-doc-drift
- **Severity**: important
- **Concern**: The generic shared validator-failure Fix/Override bullets still allow or prescribe bare `ACTION=VALIDATE_PLAN_COMMANDS` on `composed-plan.md` and generic success continuation. At the Step 5c `design-publish.sh` site, that can bypass the folded redact/publish/rename driver path, skip Gate C completion, or avoid the intended rc-4 retry loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Innovation: Restrict generic bullets to `plan.txt` sites only, or add explicit precedence: at `design Step 5c`, Fix/Override/Cancel follow only the `--site design Step 5c` bullets (`design-publish.sh` re-capture; Override uses `--skip-validate`); update **Cancel** Step 5c text to items 3–5 gating instead of listing redact/publish steps that the driver now owns
  - From Cursor-Edge: Rewrite generic Fix/Override to plan.txt-only or subordinate them to the Step 5c site branch that re-captures design-publish.sh
  - From Cursor-Requirements: Retarget the shared section trigger to VALIDATE_STATUS=defects-found (plan.txt via postplan/inline capture; Step 5c via design-publish exit 4). Limit the generic Fix-and-retry bullet to plan.txt; defer composed-plan.md solely to the --site design Step 5c branch (design-publish re-capture / --skip-validate)
  - From Cursor-dyn-cross-doc-drift: Scope generic Fix/Override to plan.txt only, or add explicit supersession prose (“When --site is design Step 5c, follow the site branch; do not use the generic Fix/Override bullets”) and update Override for Step 5c to re-capture design-publish.sh --skip-validate instead of “continue surrounding success path”


