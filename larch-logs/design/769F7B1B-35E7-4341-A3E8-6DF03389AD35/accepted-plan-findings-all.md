### FINDING_1: Conflated /issue and /block-issue add-blocked-by contracts
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-contract-tracer, Codex-dyn-contract-tracer, Cursor-dyn-dual-entrypoint-adapter, Codex-dyn-dual-entrypoint-adapter
- **Severity**: important
- **Concern**: The plan conflates the /issue REST dependency helper contract with the /block-issue GraphQL contract. /issue expects BLOCKED_BY_ADDED/BLOCKED_BY_FAILED stdout keys, while /block-issue expects SUCCESS=true plus confirmation output. A shared or wrongly emitted adapter can break /issue Step 6, rollback handling, /block-issue, and /combine-issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Implement block_issue_add_blocked_by_main as a separate GraphQL path preserving SUCCESS=true and confirmation-line stdout; keep issue add_blocked_by_main on the REST contract only.
  - From Codex-Arch: Specify byte-exact create-one output including ISSUE_TITLE, DRY_RUN, DRY_RUN_TITLE, DRY_RUN_LABELS, and DRY_RUN_BODY_PREVIEW. Keep /issue add-blocked-by on BLOCKED_BY_ADDED/BLOCKED_BY_FAILED plus CLIENT/BLOCKER/ERROR, and keep /block-issue on SUCCESS=true plus confirmation.
  - From Cursor-Innovation: Port block_issue_add_blocked_by_main from skills/block-issue/scripts/add-blocked-by.sh (GraphQL path) as a separate function; do not delegate to issue REST add_blocked_by.
  - From Codex-Innovation: Keep separate output adapters: issue add-blocked-by must emit BLOCKED_BY_ADDED/BLOCKED_BY_FAILED/CLIENT/BLOCKER/ERROR, while block-issue keeps SUCCESS plus confirmation
  - From Cursor-Pragmatic: Split contracts: `issue add-blocked-by` must emit the `BLOCKED_BY_*` KV grammar from `skills/issue/scripts/add-blocked-by.md`; reserve `SUCCESS=true` for `block-issue add-blocked-by` only
  - From Codex-Pragmatic: Split the shared dependency core from caller-specific emitters. Preserve BLOCKED_BY_ADDED/BLOCKED_BY_FAILED/CLIENT/BLOCKER/ERROR and exit codes 0/1/2/3 for issue add-blocked-by. Keep SUCCESS=true plus confirmation only for block-issue add-blocked-by.
  - From Codex-Requirements: Preserve BLOCKED_BY_ADDED, BLOCKED_BY_FAILED, CLIENT, BLOCKER, ERROR, and exit codes for issue add-blocked-by; keep SUCCESS=true only for the block-issue adapter
  - From Cursor-dyn-contract-tracer: Replace plan claims with BLOCKED_BY_ADDED/BLOCKED_BY_FAILED CLIENT BLOCKER ERROR on contract stream; keep retry/idempotency/404 semantics from add-blocked-by.md
  - From Cursor-dyn-contract-tracer: Implement block_issue_add_blocked_by_main as separate GraphQL port preserving SUCCESS=true confirmation line and stderr ERROR=; share only redaction/helpers not REST POST logic
  - From Codex-dyn-contract-tracer: Split the two contracts: issue add-blocked-by must preserve BLOCKED_BY_ADDED/BLOCKED_BY_FAILED stdout keys and exit codes 0/1/2/3; block-issue add-blocked-by must preserve SUCCESS=true plus confirmation on stdout and ERROR on stderr.
  - From Cursor-dyn-dual-entrypoint-adapter: Plan documents add_blocked_by_main as SUCCESS=true plus a confirmation line; live /issue helper emits BLOCKED_BY_ADDED=true CLIENT= BLOCKER= on the contract stream /implement and /issue Step 6 parse BLOCKED_BY_ADDED=true; a port following plan line 36 breaks dep-edge application and orphan-close recovery In stdout KV preservation, specify add_blocked_by_main emits BLOCKED_BY_ADDED=true CLIENT= BLOCKER=; on failure BLOCKED_BY_FAILED=true and ERROR= on the same KV stream with exits 1/2/3 per add-blocked-by.md
  - From Codex-dyn-dual-entrypoint-adapter: Keep one shared add_blocked_by core for retry and idempotency, but make the /issue entrypoint emit the existing BLOCKED_BY_ADDED/BLOCKED_BY_FAILED CLIENT BLOCKER ERROR schema, and make only block_issue_add_blocked_by_main translate the shared result to SUCCESS=true plus confirmation or ERROR= on stderr.


### FINDING_2: create-one stdout schema omits required keys
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-contract-tracer, Codex-dyn-contract-tracer
- **Severity**: important
- **Concern**: The planned create_one_main contract omits ISSUE_TITLE and dry-run KV fields that /issue and test harnesses consume. This can break title-prefix propagation, ISSUE_<i>_TITLE emission, dry-run reporting, and redaction coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Specify byte-exact create-one output including ISSUE_TITLE, DRY_RUN, DRY_RUN_TITLE, DRY_RUN_LABELS, and DRY_RUN_BODY_PREVIEW. Keep /issue add-blocked-by on BLOCKED_BY_ADDED/BLOCKED_BY_FAILED plus CLIENT/BLOCKER/ERROR, and keep /block-issue on SUCCESS=true plus confirmation.
  - From Codex-Pragmatic: Preserve the full create-one stdout schema, including ISSUE_TITLE on success and dry-run, plus the existing DRY_RUN_* fields.
  - From Codex-Requirements: Preserve the full create-one output schema from create-one.md, including ISSUE_TITLE, DRY_RUN_TITLE, DRY_RUN_LABELS when present, and DRY_RUN_BODY_PREVIEW
  - From Cursor-dyn-contract-tracer: Add ISSUE_TITLE on success; document DRY_RUN=true DRY_RUN_TITLE ISSUE_TITLE optional DRY_RUN_LABELS DRY_RUN_BODY_PREVIEW; preserve exit codes 0/1/2/3 per skills/issue/scripts/create-one.sh
  - From Codex-dyn-contract-tracer: Expand create_one_main’s contract to include ISSUE_TITLE on real-create success, and DRY_RUN=true, DRY_RUN_TITLE, ISSUE_TITLE, optional DRY_RUN_LABELS, and optional DRY_RUN_BODY_PREVIEW on dry-run success.


### FINDING_3: Non-SKILL issue helper consumers are not cut over
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan deletes issue helper scripts before migrating direct non-SKILL consumers. /implement OOS helpers, /research tests, audit-runs filing, and other harnesses can invoke deleted parse-input or create-one paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these consumers and their docs/tests to UPDATED, invoke python3 .../python/cli.py issue parse-input or issue create-one directly, and include them in parity coverage before deleting the bash files.
  - From Codex-Pragmatic: Retarget every live direct consumer to python3 "$REPO_ROOT/python/cli.py" issue parse-input or alias resolve-target before deleting the shell files, and update the corresponding Makefile/docs references.
  - From Cursor-Requirements: Repointer both implement helpers (and test-stall-recovery-report.sh parse-input cases) to python3 cli.py issue parse-input with the same argv contract
  - From Codex-Requirements: Add these consumers and tests to the direct CLI cutover, or keep shared files out of the retired set until all callers are migrated


### FINDING_4: Alias resolve-target harness remains wired to deleted shell path
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan ports alias coverage to Python but leaves the old resolve-target shell harness and lint/docs references wired. make lint and retired-script checks can fail after resolve-target.sh is deleted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Retire or retarget test-alias-target-resolution alongside python/test_alias_skill.py. Remove it from Makefile shards and .PHONY, update agent-lint.toml, and update docs/linting.md.
  - From Codex-Pragmatic: Retarget every live direct consumer to python3 "$REPO_ROOT/python/cli.py" issue parse-input or alias resolve-target before deleting the shell files, and update the corresponding Makefile/docs references.
  - From Codex-Requirements: Add these consumers and tests to the direct CLI cutover, or keep shared files out of the retired set until all callers are migrated


### FINDING_5: upgrade-larch release and library callers still reference deleted shell files
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan deletes upgrade-larch shell files and small shared libraries while release and live scripts still reference them. Release Step 7, stale-plugin checks, or session health flows can fail with missing paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Update release Step 7 to call the new Python upgrade-larch entrypoint and Python root-resolution behavior, or keep the shell files live until release is cut over.
  - From Codex-Requirements: Add these consumers and tests to the direct CLI cutover, or keep shared files out of the retired set until all callers are migrated


### FINDING_6: Required make lint validation is missing
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan’s final validation omits make lint even though the definition of done requires it alongside py-lint and py-test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add make lint to the final validation commands before merge


### FINDING_7: parse-input contract changes optional OOS key emission
- **Reviewer(s)**: Cursor-dyn-contract-tracer
- **Severity**: important
- **Concern**: The plan says parse_input_main always emits ITEM_<i>_REVIEWER, PHASE, and VOTE_TALLY. The bash helper emits those keys only when non-empty OOS fields exist, so unconditional empty keys can alter downstream KV parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-tracer: Match parse-input.sh flush_item: emit REVIEWER PHASE VOTE_TALLY only when values are non-empty; keep MALFORMED+BODY_FILE issue #138 pairing


### FINDING_8: list-issues omits archival title-prefix filtering
- **Reviewer(s)**: Cursor-dyn-contract-tracer
- **Severity**: important
- **Concern**: The plan omits the archival title-prefix jq filter used by list-issues.sh. Skipping it can change Phase 1 dedup candidate sets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-tracer: Port DEDUP_SKIP_PREFIX_FILTER from lib-title-eligibility.sh jq fragment; keep LIST_STATUS=ok|failed always exit 0 fail-open semantics


### FINDING_9: upgrade-larch stdout restore behavior is underspecified
- **Reviewer(s)**: Cursor-dyn-contract-tracer
- **Severity**: important
- **Concern**: The upgrade_larch.run_main contract omits the quiet-init and stdout restore behavior that makes claude plugin list output operator-visible. Porting only restart/version lines can change what users and automation see.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-tracer: Document and port quiet_init plus post-init stdout restore (exec 1>&3 equivalent) and which lines use BreadcrumbWriter vs restored stdout


### FINDING_10: list-issues fail-open exit contract is missing
- **Reviewer(s)**: Codex-dyn-contract-tracer
- **Severity**: important
- **Concern**: The plan does not state list_issues_main’s always-exit-0 fail-open behavior. If the Python port exits non-zero on snapshot failure, /issue can abort instead of parsing LIST_STATUS=failed and falling back to create-all.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-tracer: Add the exit-code contract: list_issues_main must always exit 0 for helper failures, emit LIST_STATUS=failed on stdout with no TSV rows, and route warnings to stderr.


### FINDING_11: write-sentinel status must remain stderr-only
- **Reviewer(s)**: Codex-dyn-contract-tracer
- **Severity**: important
- **Concern**: The plan both says write_sentinel_main status goes to stderr and says all issue_create.py functions emit through contract_stream. Emitting WROTE or ERROR on stdout would corrupt the /issue stdout grammar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-tracer: Carve out write_sentinel_main from the contract_stream rule. Emit WROTE and ERROR through the stderr diagnostic path only, and keep stdout empty for this helper.


### FINDING_12: upgrade-larch stderr machine keys are omitted
- **Reviewer(s)**: Codex-dyn-contract-tracer
- **Severity**: important
- **Concern**: The upgrade_larch.run_main contract omits stderr machine keys that /release Step 7 parses. Dropping them can hide cone repair, new-version install, and restart-required state from release automation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-tracer: State the full machine-readable stderr contract: LARCH_CONE_RECONCILED=true|false, LARCH_NEW_VERSION_INSTALLED=true, and LARCH_RESTART_REQUIRED=true, with the same conditions as upgrade-larch.sh.


### FINDING_13:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:13; plan.txt:79-80; plan.txt:132-146; scripts/check-stale-plugin.sh:32; skills/implement/scripts/stall-recovery-report.sh:14; scripts/sessionstart-health.sh:73-82; .claude/skills/release/SKILL.md:191-220
- **Concern**: [SCOPE-REDUCTION] Shared sourced libraries are folded into upgrade_larch and deleted while live shell consumers remain. Scenario: Deleting scripts/lib-larch-dev-clone.sh, scripts/lib-sparse-dirs.sh, and release-step7-root.sh breaks check-stale-plugin, stall-recovery-report, and release Step 7. It also silently disables the SessionStart sparse drift probe.
- **Proposed resolution**: Either keep these sourced-only shared libs out of the retired set for this PR, or explicitly cut every current consumer to new cli.py verbs before adding the files to python/migrated-scripts.tsv.


### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/stall-recovery-report.sh:12-15; scripts/check-stale-plugin.sh:31-33; scripts/sessionstart-health.sh:73-75
- **Concern**: [SCOPE-REDUCTION] Plan retires shared shell libraries that are still used outside /upgrade-larch. Scenario: lib-larch-dev-clone.sh is hard-sourced by stall recovery and stale-plugin checks, so deletion breaks those scripts. lib-sparse-dirs.sh is sourced by SessionStart sparse-cone drift detection, so deletion silently disables that existing hook check.
- **Proposed resolution**: Remove scripts/lib-larch-dev-clone.sh and scripts/lib-sparse-dirs.sh from the absorbed/deleted/migrated list for this small-skill port, unless the same plan also cuts over all listed non-upgrade consumers.




### FINDING_1: Python issue publication redaction would miss Cursor CLI keys
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Moving issue publication redaction to `python/redact.py` would lose current outbound `crsr_` secret redaction coverage, so issue text or captured `gh` errors may publish Cursor CLI keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update python/redact.py to match the shell outbound redaction families before using it for issue_create, or keep create-one on scripts/redact-secrets.sh; add a crsr_ parity case to the ported tests


### FINDING_2: Deleted block-issue helper still has a live combine-issues caller
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-call-site-sweep, Codex-dyn-call-site-sweep
- **Severity**: important
- **Concern**: The plan deletes `skills/block-issue/scripts/add-blocked-by.sh` but omits the direct `.claude/skills/combine-issues/SKILL.md` call site, so `/combine-issues` blocked-by wiring would call a missing script and retired-path lint may fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add an UPDATED entry for .claude/skills/combine-issues/SKILL.md and retarget the call to python3 "$PWD/python/cli.py" block-issue add-blocked-by <N> <M>
  - From Cursor-Pragmatic: Add `.claude/skills/combine-issues/SKILL.md` to UPDATED files; replace the fence with `python3 "$PWD/python/cli.py" block-issue add-blocked-by <N> <M>`
  - From Codex-Pragmatic: Add .claude/skills/combine-issues/SKILL.md to the UPDATED list and invoke python3 "$PWD/python/cli.py" block-issue add-blocked-by <N> <M>
  - From Cursor-Requirements: Add `.claude/skills/combine-issues/SKILL.md` to UPDATED surfaces; replace the bash fence with `python3 "$PWD/python/cli.py" block-issue add-blocked-by <N> <M>`
  - From Codex-Requirements: Add .claude/skills/combine-issues/SKILL.md to the cutover list and replace the invocation with the block-issue Python CLI verb
  - From Cursor-dyn-call-site-sweep: Add .claude/skills/combine-issues/SKILL.md to ### UPDATED and replace the fence with python3 python/cli.py block-issue add-blocked-by <N> <M> (or invoke /block-issue), matching the block-issue SKILL cutover
  - From Codex-dyn-call-site-sweep: Add .claude/skills/combine-issues/SKILL.md to UPDATED and replace the direct script call with python3 "$PWD/python/cli.py" block-issue add-blocked-by <N> <M>


### FINDING_3: Retired-path sweep misses tracked references
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-call-site-sweep
- **Severity**: important
- **Concern**: After adding retired bash paths to `python/migrated-scripts.tsv`, tracked files still contain full repo-relative references to deleted scripts, so `lint-retired-scripts` and `make lint` may fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add these retained files to the UPDATED list and replace full deleted script paths with the Python CLI or neutral precedent prose before running lint-retired-scripts.
  - From Codex-dyn-call-site-sweep: Add these files to UPDATED or make the stale-reference sweep explicitly cover them, replacing deleted script paths with the new Python CLI paths or live non-retired references


### FINDING_4: fetch-issue-details exit contract is overstated
- **Reviewer(s)**: Cursor-dyn-contract-witness
- **Severity**: important
- **Concern**: The plan says `issue fetch-issue-details` always exits 0, but the current helper exits 1 for usage and validation errors and only guarantees exit 0 for per-issue partial fetch failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-witness: Amend the plan contract to match `fetch-issue-details.md`: exit 0 for per-issue partial failure; exit 1 for missing/empty `--numbers` or `--output`, unknown flags, and invalid `--max-comments` / `--max-body-chars`.


### FINDING_5: parse-input BODY_FILE emission must stay conditional
- **Reviewer(s)**: Codex-dyn-contract-witness
- **Severity**: important
- **Concern**: The plan does not preserve that `ITEM_<i>_BODY_FILE` is emitted only when an item has a non-empty body, which could change the parser stdout grammar for title-only malformed items.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-witness: Revise plan to say BODY_FILE is emitted only when the body is non-empty; issue #138 malformed emits BODY_FILE plus MALFORMED, but title-only malformed emits TITLE plus MALFORMED only


### FINDING_6: write-sentinel stderr grammar must distinguish success from skipped states
- **Reviewer(s)**: Codex-dyn-contract-witness
- **Severity**: important
- **Concern**: The plan collapses `WROTE=true` and `WROTE=false REASON=...` stderr forms, which may emit `REASON` on success and break the current sentinel contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-witness: Revise plan to state success emits exactly WROTE=true; skipped dry-run emits WROTE=false REASON=dry_run; skipped failures emits WROTE=false REASON=failures


### FINDING_7: block-issue verification mismatch must remain warn-only
- **Reviewer(s)**: Codex-dyn-contract-witness
- **Severity**: important
- **Concern**: The plan treats blocked-by membership verification mismatch as a failure path, but the current helper warns and still reports success after a successful mutation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-witness: Revise plan and test wording to preserve warn-only verification mismatch: emit WARNING on stderr, then SUCCESS=true and the confirmation line on stdout


### FINDING_8:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/skills/combine-issues/SKILL.md:104
- **Concern**: [SCOPE-REDUCTION] Live `/combine-issues` still invokes deleted `skills/block-issue/scripts/add-blocked-by.sh`. Scenario: After the hard cutover, OOS blocked-by wiring calls a removed script; `make lint-retired-scripts` also fails on the lingering full path
- **Proposed resolution**: Retarget to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" block-issue add-blocked-by <N> <M>` (or equivalent `$PWD/python/cli.py` in that skill) and add this file to the plan’s explicit cutover list


### FINDING_9:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:127-133; skills/block-issue/scripts/add-blocked-by.sh:128-135
- **Concern**: [SCOPE-REDUCTION] /block-issue changes membership-verification miss from warning success to hard failure. Scenario: The current helper emits WARNING on uncertain same-response membership but still exits success after the mutation succeeds; the plan would make that a nonzero ERROR, breaking the exact-port contract
- **Proposed resolution**: Preserve the existing warning-plus-success behavior for this case, or explicitly limit failure to lookup and mutation errors


### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/combine-issues/SKILL.md:104
- **Concern**: [SCOPE-REDUCTION] Live call site still invokes deleted `skills/block-issue/scripts/add-blocked-by.sh` but the plan has no cutover entry for combine-issues. Scenario: After bash deletion `/combine-issues` OOS blocked-by wiring fails at runtime while other `/block-issue` paths work
- **Proposed resolution**: Add `.claude/skills/combine-issues/SKILL.md` to the call-site sweep: replace the shell helper with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" block-issue add-blocked-by`


### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-redact-secrets.sh:341-358
- **Concern**: [SCOPE-REDUCTION] Missing-shell-redactor test conflicts with the planned redact.py port. Scenario: The plan says issue_create.py uses python/redact.py, but also keeps a create-one failure test based on missing scripts/redact-secrets.sh; that either fails against the Python port or forces an unnecessary shell-helper dependency
- **Proposed resolution**: Keep redacted title body and error integration coverage, but remove the missing scripts/redact-secrets.sh create-one assertion unless the plan explicitly keeps shell redaction for create-one


### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/block-issue/scripts/add-blocked-by.sh:128-135
- **Concern**: [SCOPE-REDUCTION] Plan changes warn-only membership uncertainty into a hard failure. Scenario: Current /block-issue emits WARNING then SUCCESS when addBlockedBy succeeds but returned blockedBy nodes omit the blocker; the plan's membership-verification-failure test implies exit 1, which is a behavior change beyond an exact port
- **Proposed resolution**: Preserve the existing warn-only SUCCESS=true behavior for this case, and make the pytest assert warning plus success unless the issue explicitly requests fail-closed semantics


