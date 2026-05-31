### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:339-355 vs plan design-init-runparams.sh step 5
- **Concern**: Plan calls the #3008 jq-merge “relocated verbatim” but only quotes the jq filter expression, not the full block that logs merge failures via append-tool-ffailure.sh. Scenario: On jq failure, execution-issues.md loses the Warnings entry that exists today; contradicts “Observable behavior is preserved”
- **Proposed resolution**: Copy the entire merge block from today’s Step 0b (mktemp paths, append-tool-failure site design Step 0b, and both warning strings) into design-init-runparams.sh step 5 and pin it in the harness

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:204-210
- **Concern**: Step 0b handoff cites phase_driver_read_result_env with stdout fallback but lib API is file-only. Scenario: phase_driver_read_result_env reads only a path; it does not merge captured driver stdout. Step 3 uses a manual file-first case loop plus a second loop over _plan_review_out (skills/design/SKILL.md:860-888). A fence that only calls the helper loses stdout fallback when .design-route-result.env is missing or symlink-refused, and the function is undefined unless lib-phase-driver.sh is sourced in SKILL prose (not specified).
- **Proposed resolution**: Mirror the existing Step 3 handoff shape: set +e capture _route_rc and _route_out, file-first allowlisted case read of .design-route-result.env, then stdout merge for missing keys; abort on _route_rc=2/other non-zero before ROUTE branches. Do not rely on phase_driver_read_result_env alone in the orchestrator unless the plan adds an explicit source line and a separate stdout loop.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:228-231
- **Concern**: design-init-runparams.sh lacks symmetric exit-code fence in the planned SKILL rewrite. Scenario: design-route.sh gets explicit set +e, exit 2, and abort-on-non-zero guards (plan FINDING_3). The post-gate init driver section only mentions INIT_STATUS=contract-drift. argv/config exit 2 or unexpected non-zero from design-init-runparams.sh could fall through without abort, unlike route and Step 3 config handling.
- **Proposed resolution**: Add the same fence pattern as design-route: capture _init_rc with set +e; on exit 2 print a configuration-error banner and exit 1 without reading INIT_STATUS; on other non-zero abort before proceeding; only on exit 0 read .design-init-runparams-result.env (file-first plus stdout merge) and then handle INIT_STATUS=contract-drift.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:757-765
- **Concern**: Check 20 still pins removed Step 0b sub-step numbers. Scenario: After SKILL.md drops 2.5/2.5-bis/5.5-bis anchors, greps for 2.5 Title-eligibility and the fetch_line/filter_line/clarify_line ordering test will fail unless replaced. The plan says adjust ordering checks but does not name replacement literals.
- **Proposed resolution**: make lint fails on first structure run after SKILL rewrite When re-pointing Check 20/21, replace fetch→2.5→3 line-order asserts with stable anchors (e.g. design-route.sh invocation before clarify loop, cancel-title-filter ROUTE handling before clarify) and drop 2.5-bis/5.5-bis SKILL greps in favor of design-route.sh / design-init-runparams.sh pins already listed elsewhere in the plan.

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-kv-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:228-231 (proposed skills/design/SKILL.md Step 0b)
- **Concern**: `design-init-runparams.sh` handoff lacks exit-code guards parallel to `design-route.sh`. Scenario: Proposed SKILL rewrite only handles `INIT_STATUS=contract-drift` after the init fence; driver spec allows exit 2 for argv/config (`plan.txt:187`) and exit 1 for contract drift. On exit 2 or unexpected non-zero without a reliable result env, orchestrator may continue Step 0b as if init succeeded (same class as failure mode 6 for route, but unmitigated for init).
- **Proposed resolution**: Add `set +e` / `_init_rc` capture mirroring `plan.txt:204-209`: abort `/design` on exit 2 (configuration error banner) and on any other non-zero except the explicit contract-drift path; read `.design-init-runparams-result.env` only when `_init_rc=0`. Pin in `scripts/test-design-structure.sh` alongside FINDING_3 route greps.
