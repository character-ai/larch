Normalizing the supplied reviewer findings: merging duplicates (FINDING_3 and FINDING_5 share the same init exit-code risk) and producing the structured aggregator output.
Orchestrator aggregation of the five reviewer slots. **FINDING_3** and **FINDING_5** describe the same behavioral risk (missing init-driver exit-code fence vs. `design-route.sh`); merged into one block with severity **important**. All other inputs are distinct fixes or code paths and remain separate.

### FINDING_1: Incomplete jq-merge block drops Warnings logging on failure
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan treats the #3008 jq-merge as “relocated verbatim” but only quotes the jq filter expression, not the full Step 0b block that logs merge failures via `append-tool-failure.sh`. If jq fails, `execution-issues.md` may lose the Warnings entry that exists today, contradicting “Observable behavior is preserved.”
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Copy the entire merge block from today’s Step 0b (mktemp paths, append-tool-failure site design Step 0b, and both warning strings) into design-init-runparams.sh step 5 and pin it in the harness

### FINDING_2: Step 0b handoff must not rely on file-only `phase_driver_read_result_env`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Step 0b handoff cites `phase_driver_read_result_env` with stdout fallback, but the lib API is file-only. That helper reads only a path and does not merge captured driver stdout. Step 3 uses a manual file-first case loop plus a second loop over `_plan_review_out`. A fence that only calls the helper loses stdout fallback when `.design-route-result.env` is missing or symlink-refused, and the function is undefined unless `lib-phase-driver.sh` is sourced in SKILL prose (not specified).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mirror the existing Step 3 handoff shape: set +e capture _route_rc and _route_out, file-first allowlisted case read of .design-route-result.env, then stdout merge for missing keys; abort on _route_rc=2/other non-zero before ROUTE branches. Do not rely on phase_driver_read_result_env alone in the orchestrator unless the plan adds an explicit source line and a separate stdout loop.

### FINDING_3: `design-init-runparams.sh` handoff lacks exit-code fence parallel to route
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-kv-contract
- **Severity**: important
- **Concern**: The planned SKILL rewrite gives `design-route.sh` explicit `set +e`, exit 2, and abort-on-non-zero guards, but the post-gate init driver section only mentions `INIT_STATUS=contract-drift`. The driver spec allows exit 2 for argv/config and exit 1 for contract drift. On exit 2 or unexpected non-zero without a reliable result env, the orchestrator may continue Step 0b as if init succeeded—the same failure class as unmitigated route handling, but unaddressed for init.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add the same fence pattern as design-route: capture _init_rc with set +e; on exit 2 print a configuration-error banner and exit 1 without reading INIT_STATUS; on other non-zero abort before proceeding; only on exit 0 read .design-init-runparams-result.env (file-first plus stdout merge) and then handle INIT_STATUS=contract-drift.
  - From Cursor-dyn-kv-contract: Add `set +e` / `_init_rc` capture mirroring `plan.txt:204-209`: abort `/design` on exit 2 (configuration error banner) and on any other non-zero except the explicit contract-drift path; read `.design-init-runparams-result.env` only when `_init_rc=0`. Pin in `scripts/test-design-structure.sh` alongside FINDING_3 route greps.

### FINDING_4: Check 20 still pins removed Step 0b sub-step numbers
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Concern**: Check 20 in `scripts/test-design-structure.sh` still greps removed Step 0b sub-step numbers (2.5, 2.5-bis, 5.5-bis). After SKILL.md drops those anchors, greps for 2.5 title-eligibility and fetch_line/filter_line/clarify_line ordering will fail unless replaced. The plan says to adjust ordering checks but does not name replacement literals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: make lint fails on first structure run after SKILL rewrite When re-pointing Check 20/21, replace fetch→2.5→3 line-order asserts with stable anchors (e.g. design-route.sh invocation before clarify loop, cancel-title-filter ROUTE handling before clarify) and drop 2.5-bis/5.5-bis SKILL greps in favor of design-route.sh / design-init-runparams.sh pins already listed elsewhere in the plan.
