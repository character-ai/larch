### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:1577-1581
- **Concern**: Shared validator-failure Fix/Override bullets still prescribe standalone ACTION=VALIDATE_PLAN_COMMANDS and continuing the surrounding success path, which matched pre-fold Step 5c items 2-3. Scenario: After folding validate+redact into design-publish.sh, Fix-and-retry that re-runs only VALIDATE_PLAN_COMMANDS leaves composed-plan.md unredacted/unpublished; Override that continues the surrounding path has no redact/publish steps left to continue
- **Proposed resolution**: In ### Plan command validator failure (shared), site-branch Step 5c: Fix re-runs design-publish.sh after composed-plan.md edits; Override/Accept re-runs design-publish.sh --skip-validate (Warnings append retained); keep plan.txt sites on design-postplan-emit / VALIDATE_PLAN_COMMANDS semantics


### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:29,560,1540; scripts/test-render-cost-line-callsites.sh:62
- **Concern**: Anti-halt and global summary prose still gate only on `_publish_rc` 0/1/3; `test-render-cost-line-callsites.sh` hard-pins that substring. Scenario: After `design-publish.sh` exit 4, the global “continue after every Bash” rule can push the orchestrator into Step 5c items 5–7/5d before the shared validator handler/retry loop; the cost-line harness blocks any anti-halt edit that mentions rc 4
- **Proposed resolution**: Amend anti-halt, Final summary block, and Step 5d recap gates to state rc 4 must run the Step 5c shared-handler retry loop (no final-summary/sentinel/footer) until a later rc is 0/1/3; update the `test-render-cost-line-callsites.sh` pin accordingly


### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1579,1420-1532
- **Concern**: Shared **Fix-and-retry** still mandates `ACTION=VALIDATE_PLAN_COMMANDS`; Step 5c fold only documents `design-publish.sh` retries. Scenario: Operator Fix at Step 5c may re-run `invoke-plan-validator.sh` without recomposing or without a full publish retry, leaving stale `composed-plan.md` or skipping redact/publish while the folded driver owns both
- **Proposed resolution**: For `--site` `design Step 5c`, amend the shared Fix bullet (or add a site override): edit `composed-plan.md` (re-compose item 1 when `plan.txt` changed), then re-capture `design-publish.sh` only—do not call `invoke-plan-validator.sh` standalone


### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:1348-1381; skills/design/SKILL.md:1477,1521
- **Concern**: `test-design-structure.sh` greps hard-pin `{0,1,3}` contract strings; plan widens the unexpected-rc guard to include 4 but does not list reconciling those pins. Scenario: `make test-design-structure` may fail after widening the guard, or pins may block the guard change
- **Proposed resolution**: Extend the `test-design-structure.sh` section to retire/replace pins at 1348/1374/1380 and add explicit asserts that rc 4 is handled before items 5–7 (per the plan’s own failure-mode mitigation)


### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:30-32
- **Concern**: Step 5c item references still say items 5-7 after deleting inline validate/redact. Scenario: The plan renumbers publish to item 2 and drops old items 2-3, but retry/rc-4 prose still gates on items 5-7; implementers can wire final-summary, step-5c sentinel, or cleanup to the wrong step numbers
- **Proposed resolution**: After renumber, use one index set everywhere (e.g. items 3-5 for summary, sentinel, plan-write-failure) and update Failure modes / test-design-structure pins that mention 5-7


### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:1575-1581
- **Concern**: Shared Fix-and-retry still mandates ACTION=VALIDATE_PLAN_COMMANDS for composed-plan.md. Scenario: After folding validation into design-publish.sh, a Step 5c Fix that only re-runs invoke-plan-validator can pass validation but never redact/publish, or diverge from the documented retry loop (re-capture design-publish.sh)
- **Proposed resolution**: Add an explicit Step 5c branch under Fix-and-retry: edit composed-plan.md, then re-run the Step 5c design-publish.sh capture (normal path); reserve bare VALIDATE_PLAN_COMMANDS for plan.txt sites only


### FINDING_7:
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-dyn-contract-ledger
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lint-skill-md-flag-signature.sh:121-153
- **Concern**: Plan drops review-budget from fixture script flag lists but not from the fixture invocation. Scenario: The multiline_good and regression_fixed fixtures would still invoke --review-budget after their fake write-run-params.sh declarations drop it, so this harness can fail under make lint
- **Proposed resolution**: Remove the --review-budget "$review_budget" line from the generated SKILL.md fixture too, keeping the fake script declarations and fixture invocation in sync


### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-driver.md:9-10
- **Concern**: Primary Callers still say Step 5c runs VALIDATE_PLAN_COMMANDS before redact-secrets.sh in the orchestrator. Scenario: Readers and implementers keep the old split-driver model after the fold; doc contradicts design-publish.md and SKILL.md Step 5c
- **Proposed resolution**: Add design-driver.md to the plan (or Edit-in-sync on design-publish.md): state composed-plan validation runs inside design-publish.sh before redaction


### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1417
- **Concern**: Step 5b handoff prose still says Step 5c is compose → validate → redact → design-publish.sh. Scenario: Operators and reviewers follow a 3-call Step 5c flow the PR removes; drift from the single-driver contract
- **Proposed resolution**: Update the Step 5b continue line to compose composed-plan.md then one design-publish.sh call (validate, redact, publish inside the driver)


### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1579-1580
- **Concern**: Shared Fix-and-retry bullet still ends with re-run ACTION=VALIDATE_PLAN_COMMANDS on composed-plan.md. Scenario: Fix after exit 4 may invoke only invoke-plan-validator.sh and never redact/publish, leaving Gate C unfinished
- **Proposed resolution**: For the Step 5c site, state Fix re-runs design-publish.sh after user-approved edits; reserve bare VALIDATE_PLAN_COMMANDS for plan.txt sites only


### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/SKILL.md:1580-1581
- **Concern**: Step 5c Override/Accept site only specifies --skip-validate retry, not the generic Override Warnings append. Scenario: Operator override of composed-plan defects can publish without an execution-issues.md audit entry (regression vs plan.txt Override)
- **Proposed resolution**: Keep append-tool-failure.sh Warnings (site design Step 5c, validate-plan-commands.log) before the --skip-validate design-publish.sh retry, matching other sites


### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.md:5
- **Concern**: Caller line still says Step 5c invokes the driver after items 1–3. Scenario: Minor contract drift from the folded Step 5c (compose only, then one driver call)
- **Proposed resolution**: Change Caller to after item 1 (compose composed-plan.md) on Gate-C-approved runs


### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lint-skill-md-flag-signature.sh:111-136
- **Concern**: Plan updates the fixture script flag lists but is silent on removing the fixture SKILL.md --review-budget invocation. Scenario: The multiline_good and regression_fixed fixture scripts would no longer declare review-budget while their heredoc still invokes --review-budget, so test-lint-skill-md-flag-signature fails under make lint
- **Proposed resolution**: Revise the plan to remove the --review-budget "$review_budget" line from the fixture SKILL.md heredoc wherever the fixture write-run-params.sh flag list drops review-budget


### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-contract-ledger
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1577-1581
- **Concern**: Shared ### Plan command validator failure (shared) Fix-and-retry still ends with re-run ACTION=VALIDATE_PLAN_COMMANDS on the target file; Step 5c site text only says return to the retry loop. Scenario: After folding validate+redact into design-publish.sh, a Fix on composed-plan.md can re-validate without redacting/publishing, or skip the driver retry contract the Step 5c rc=4 loop depends on
- **Proposed resolution**: Revise the shared handler: for site design Step 5c, Fix edits composed-plan.md then re-runs the Step 5c design-publish.sh capture (no --skip-validate); reserve --skip-validate for Override/Accept only


### FINDING_15:
- **Reviewer(s)**: Codex-dyn-contract-ledger
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-publish.md:22-24,48-52; skills/design/scripts/design-publish.sh:209-365
- **Concern**: design-publish.md has stale publish-tail order and pre-publish summary claims that the plan does not explicitly replace. Scenario: The post-change doc can still claim design_reentry_marker_write runs before publish/rename and that render-final-summary.sh --pre-publish-only runs, while the script runs diagrams, publish, post-publish summary, rename, then marker
- **Proposed resolution**: Explicitly update the design-publish.md responsibility and ordering bullets to the actual script order and remove the pre-publish-only claim


### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-retry-state
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1577-1581
- **Concern**: Shared Fix-and-retry still ends in ACTION=VALIDATE_PLAN_COMMANDS only. Scenario: After fold, Step 5c Fix that only re-validates never runs redact/plan-block-write/publish; operator loops on defects without finishing Gate C
- **Proposed resolution**: For site design Step 5c, replace the generic re-validate tail with: after edits, re-run Step 5c item 1 when plan.txt changed, then re-invoke design-publish.sh (or --skip-validate after Override); keep VALIDATE_PLAN_COMMANDS loop only for plan.txt sites


### FINDING_17:
- **Reviewer(s)**: Codex-dyn-retry-state
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1489-1514; skills/design/scripts/lib-phase-driver.sh:40-56
- **Concern**: Step 5c retry plan reuses the existing file-first parse path without clearing a prior .design-publish-result.env. Scenario: Result-env write failure on a Fix or Override retry can leave the rc4 defects-found env from the first attempt in place; the file-first parser then keeps stale PLAN_WRITE_OK or VALIDATE_STATUS and ignores current stdout, so final summary, step-5c sentinel, footer, or cleanup decisions can reflect the failed attempt
- **Proposed resolution**: Before each design-publish.sh attempt in Step 5c, remove or quarantine .design-publish-result.env; alternatively, when _publish_rc=3 parse stdout as authoritative and do not read an existing result env. Add the same rule to the retry prose and narrow structure/test coverage.


### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-harness-matrix
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1577-1581
- **Concern**: Shared ### Plan command validator failure (shared) Fix-and-retry still tells the orchestrator to re-run bare ACTION=VALIDATE_PLAN_COMMANDS on composed-plan.md after edits. Scenario: After Step 5c folds validate+redact+publish into design-publish.sh, Fix can re-validate without redacting or publishing, or skip redaction while the driver still requires composed-plan.redacted.md for plan-block-write
- **Proposed resolution**: In that section, state that for --site design Step 5c, Fix-and-retry means re-invoke design-publish.sh without --skip-validate after the operator edits composed-plan.md; reserve bare VALIDATE_PLAN_COMMANDS for plan.txt sites only


### FINDING_19:
- **Reviewer(s)**: Codex-dyn-harness-matrix
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-publish.sh:71-125,232-245
- **Concern**: Proposed publish harness does not assert the empty or not-run validator-status infra-failure branch. Scenario: design-publish.sh could accept an invoke-plan-validator.sh run that exits 0 but emits no VALIDATE_STATUS or emits VALIDATE_STATUS=not-run, then redact and publish an unvalidated composed plan
- **Proposed resolution**: Add a test-design-publish case where the validator stub exits 0 with no VALIDATE_STATUS or not-run, and assert exit 2 plus no redact, plan-block-write, publish, rename, or marker


### FINDING_20:
- **Reviewer(s)**: Codex-dyn-harness-matrix
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/test-design-publish.sh:199-207
- **Concern**: The plan replaces the old empty-redacted precondition test but does not add a post-redaction empty-output assertion. Scenario: An implementation could handle redactor nonzero failures but still publish a zero-byte composed-plan.redacted.md when redact-secrets.sh exits 0 with empty stdout
- **Proposed resolution**: Add a distinct redactor-empty case with non-empty composed-plan.md and a redactor stub that exits 0 with no output; assert exit 2 and no publish-tail side effects


### FINDING_21:
- **Reviewer(s)**: Codex-dyn-harness-matrix
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-publish.sh:232-245
- **Concern**: Skip-validate harness checks publish side effects but not the result-env skip status. Scenario: Override/Accept retry could publish with --skip-validate while omitting VALIDATE_STATUS=skipped, leaving Step 5c retry parsing ambiguous or stale
- **Proposed resolution**: Add a --skip-validate assertion that .design-publish-result.env contains VALIDATE_STATUS=skipped, alongside the existing validator-stub-not-consulted and publish-tail assertions


