### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1577-1581
- **Concern**: Shared handler generic Fix/Override bullets still prescribe composed-plan `ACTION=VALIDATE_PLAN_COMMANDS` and generic Override continuation. Scenario: Step 5c `--site` branch forbids bare composed validation, but generic **Fix-and-retry** still ends with `ACTION=VALIDATE_PLAN_COMMANDS` on `composed-plan.md` and **Override** still says continue the surrounding success path; an orchestrator can skip `design-publish.sh` re-capture (no redact/publish) or publish without the folded driver
- **Proposed resolution**: Restrict generic bullets to `plan.txt` sites only, or add explicit precedence: at `design Step 5c`, Fix/Override/Cancel follow only the `--site design Step 5c` bullets (`design-publish.sh` re-capture; Override uses `--skip-validate`); update **Cancel** Step 5c text to items 3–5 gating instead of listing redact/publish steps that the driver now owns

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1489-1518
- **Concern**: Step 5c parser plan does not explicitly exempt rc 4 from the missing result-env abort. Scenario: When design-publish.sh exits 4 after defects-found and its best-effort result-env write fails, stdout has VALIDATE_STATUS but the existing guard aborts unless rc is 3, so the shared Fix/Override/Cancel handler is skipped
- **Proposed resolution**: Revise the proposed Step 5c parse fence so rc 4 also accepts stdout fallback when the result env is absent or unreadable, then route parsed VALIDATE_* values to the shared validator-failure handler instead of aborting.

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1579-1581
- **Concern**: Generic shared-handler Fix/Override still routes composed-plan retries through bare VALIDATE_PLAN_COMMANDS. Scenario: Fix/Override at Step 5c can validate without redact/publish/rename and leave Gate C unfinished
- **Proposed resolution**: Rewrite generic Fix/Override to plan.txt-only or subordinate them to the Step 5c site branch that re-captures design-publish.sh

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1515-1517
- **Concern**: Missing rc-4 carve-out on result-env parse abort guard. Scenario: rc-4 defects-found with failed env write aborts /design before the shared handler despite stdout VALIDATE_* keys
- **Proposed resolution**: Allow stdout-only parse when _publish_rc is 4 (mirror rc=3) and add a structure-test pin

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1515-1517
- **Concern**: Step 5c parse-or-abort guard still fires on rc 4 when result-env file is missing. Scenario: After defects-found, design-publish.sh exits 4 and may omit .design-publish-result.env; _publish_parse_ok stays false and the fence aborts before the shared validator handler despite VALIDATE_* on stdout
- **Proposed resolution**: Extend the guard to also skip abort when _publish_rc is 4 (mirror rc 3 stdout-authoritative handling), or require _publish_parse_ok once stdout contains VALIDATE_STATUS=defects-found

### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/write-run-params.sh:83-89; skills/design/scripts/design-postplan-emit.sh:69-72
- **Concern**: Plan removes documented compatibility flags instead of making them no-op. Scenario: Existing callers or resumed instructions that still pass --review-budget full or --force-validate will fail with unknown option even though unconditional validation does not require breaking those call sites
- **Proposed resolution**: Keep the parsers accepting these legacy flags as ignored/no-op in this PR; remove only the gating/reader behavior and defer flag/schema deletion to a separate compatibility cleanup

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1575-1581
- **Concern**: Shared validator-failure intro and Fix-and-retry bullets still prescribe ACTION=VALIDATE_PLAN_COMMANDS for composed-plan.md; plan only adds a Step 5c site branch. Scenario: After fold, Fix/Override at Step 5c can re-run bare validator + redact and skip publish, or never enter the rc-4 retry loop the plan defines
- **Proposed resolution**: Retarget the shared section trigger to VALIDATE_STATUS=defects-found (plan.txt via postplan/inline capture; Step 5c via design-publish exit 4). Limit the generic Fix-and-retry bullet to plan.txt; defer composed-plan.md solely to the --site design Step 5c branch (design-publish re-capture / --skip-validate)

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1515-1517
- **Concern**: Step 5c still has a missing-result-env abort shape that the plan does not explicitly relax for exit 4. Scenario: The plan requires defects-found to exit 4 even when .design-publish-result.env cannot be written, with stdout fallback carrying VALIDATE_STATUS. If the Step 5c parser keeps aborting when the env file is absent and rc is not 3, that promised rc-4 shared-handler path aborts instead of prompting Fix/Override/Cancel.
- **Proposed resolution**: In the Step 5c proposed parser changes, explicitly allow stdout fallback for _publish_rc=4 when VALIDATE_STATUS=defects-found is parsed, before the missing/unreadable result-env abort. Add a narrow structural/test pin for this rc-4 stdout-fallback case.

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-cross-doc-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1577-1581
- **Concern**: Shared validator-failure Fix/Override bullets still mandate bare ACTION=VALIDATE_PLAN_COMMANDS (and Override “continue surrounding success path”) for composed-plan.md; the plan only adds a Step 5c site branch and does not narrow or supersede the generic bullets. Scenario: After folding validate+redact into design-publish.sh, an orchestrator following the generic Fix bullet can re-run standalone validation on composed-plan.md, skipping redact/publish and leaving Gate C unfinished—matching the plan’s own failure mode #3
- **Proposed resolution**: Scope generic Fix/Override to plan.txt only, or add explicit supersession prose (“When --site is design Step 5c, follow the site branch; do not use the generic Fix/Override bullets”) and update Override for Step 5c to re-capture design-publish.sh --skip-validate instead of “continue surrounding success path”

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-retry-state-invariant
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1515-1517
- **Concern**: Step 5c parse-fail abort still treats rc 4 like a hard failure when `.design-publish-result.env` is absent. Scenario: Plan folds validation into `design-publish.sh` exit 4 with best-effort result-env write and stdout fallback (`plan.txt` lines 12-13, 88). The existing fence only exempts rc 3 from the `_publish_parse_ok` abort (`-ne 3`). After `rm -f .design-publish-result.env`, a defects-found attempt whose env write fails leaves `_publish_parse_ok=false` and `_publish_rc=4`, so the fence hits `exit 1` before the orchestrator can run the shared handler — breaking Fix/Override/Cancel and the stdout-fallback contract
- **Proposed resolution**: Mirror the rc 3 carve-out: change the guard to also allow `_publish_rc=4` when `_publish_out` carries `VALIDATE_*` (or drop the abort for rc 4 entirely). Pin in `scripts/test-design-structure.sh`.
