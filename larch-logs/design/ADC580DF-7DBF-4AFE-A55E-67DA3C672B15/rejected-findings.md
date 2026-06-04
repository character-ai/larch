### [Plan Review] FINDING_1

### FINDING_1: Shared Fix/Override path can still skip publish for composed-plan validation failures
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Edge, Cursor-dyn-publish-contract-threading, Cursor-dyn-operator-retry-flow
- **Severity**: important
- **Concern**: The shared validator-failure Fix/Override prose still directs composed-plan.md failures through bare `ACTION=VALIDATE_PLAN_COMMANDS`. After validation is folded into `design-publish.sh`, following that generic path for Step 5c can re-validate only, skip redact/publish, and leave Gate C unfinished.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Innovation: Rewrite the generic Fix-and-retry bullet to cover plan.txt only, or add an explicit precedence rule that design Step 5c follows the site branch and must not use bare VALIDATE_PLAN_COMMANDS on composed-plan.md
  - From Cursor-Edge: Restrict the generic Fix-and-retry bullet to plan.txt-only (EMIT_PLAN when needed then VALIDATE_PLAN_COMMANDS). Move composed-plan.md Fix/Override entirely into the --site design Step 5c bullets (design-publish.sh re-capture; --skip-validate on Override). Add a test-design-structure pin that the shared section does not pair composed-plan.md with ACTION=VALIDATE_PLAN_COMMANDS.
  - From Cursor-dyn-publish-contract-threading: Fork the shared section: restrict the generic Fix-and-retry / Override tails to plan.txt sites only (Step 2b, Gate B, discussion-round2), or add an explicit when site is design Step 5c, these bullets override the generic ones rule; require Fix/Override to rm .design-publish-result.env and re-capture design-publish.sh (Override with --skip-validate) and forbid bare ACTION=VALIDATE_PLAN_COMMANDS on composed-plan.md
  - From Cursor-dyn-operator-retry-flow: Restructure ### Plan command validator failure (shared) into explicit site branches: keep the current Fix/Override/Cancel bullets for plan.txt sites; add a design Step 5c subsection that mandates re-compose when needed, rm -f .design-publish-result.env, and foreground design-publish.sh (Override: --skip-validate only) and states composed-plan.md must not end on bare VALIDATE_PLAN_COMMANDS


