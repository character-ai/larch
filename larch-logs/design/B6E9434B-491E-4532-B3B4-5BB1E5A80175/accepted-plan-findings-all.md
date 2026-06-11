### FINDING_1: Native blocker state filter drops lowercase open blockers
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-output-parity, Codex-dyn-output-parity, Cursor-dyn-cli-entry-spec, Codex-dyn-cli-entry-spec
- **Severity**: important
- **Concern**: `native_open_blockers` compares native dependency state to uppercase `OPEN`, while the existing bash contract and stubs use lowercase `open`. This can drop native blocked-by rows and allow admission to pass an issue with open native blockers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Match blocker-helpers.sh: use case-insensitive open check or compare to open lowercase
  - From Codex-Arch: Normalize state before comparing, for example str(state).lower() == "open", and add a lowercase fixture in python/test_blocker.py
  - From Cursor-Innovation: Filter with case-insensitive open check or match lowercase open exactly as scripts/blocker-helpers.sh:50-51
  - From Codex-Innovation: Filter native blocked_by rows with state == "open" or normalize state case before comparison
  - From Cursor-Pragmatic: Filter with case-insensitive open state (e.g. str(state).lower() == "open") or match the exact lowercase literal used in scripts/blocker-helpers.sh:50-51
  - From Codex-Pragmatic: Use str(state).lower() == "open" and pin a lowercase native API fixture in python/test_blocker.py
  - From Cursor-Requirements: Add parity filter for lowercase `open` (or case-insensitive compare) matching `scripts/blocker-helpers.sh:51`
  - From Codex-Requirements: Filter lowercase open or normalize state with str(state).lower() == "open"; include a lowercase-state native blocker test
  - From Cursor-dyn-output-parity: Filter with case-insensitive open check (e.g. `str(state).lower() == "open"`) to match `scripts/blocker-helpers.sh:50-51`.
  - From Codex-dyn-output-parity: Match the predecessor by accepting lowercase `open`, or normalize state before comparison and keep only open blockers
  - From Cursor-dyn-cli-entry-spec: In native_open_blockers, match the bash contract: compare state case-insitively or use lowercase "open" for the dependencies/blocked_by payload; align test_blocker.py mocks with scripts/test-implement-admission.sh
  - From Codex-dyn-cli-entry-spec: Filter native blocked_by rows with str(state).lower() == "open" or accept both open and OPEN, and keep a unit test for lowercase API rows


### FINDING_2: Issue state and info CLIs omit repo fallback
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Codex-dyn-cli-entry-spec
- **Severity**: important
- **Concern**: `issue state` and `issue info` make `--repo` optional but omit the bash repo-resolution fallback. Existing bootstrap and finalize call sites omit `--repo`, so the Python path can query the wrong repo, fail, or return empty values where bash succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In each CLI main call gh.resolve_repo when --repo is absent before issue_state or issue_info, same pattern as clarify _resolve_repo_for_clarify
  - From Cursor-Pragmatic: Document and implement the same resolve_repo / gh.resolve_repo fallback in issue info CLI as in scripts/get-issue-info.sh:45-47 before calling issue_view_field_read
  - From Cursor-Requirements: Document and implement `gh.resolve_repo` (or equivalent) in both mains before `issue_state` / `issue_info`, mirroring `get-issue-state.sh:74-76` and `get-issue-info.sh:45-47`
  - From Codex-dyn-cli-entry-spec: Add omitted-repo handling for issue_state_main and issue_info_main: accept repo as optional, resolve with gh.resolve_repo or omit --repo when unresolved to preserve bash parity, and cover the omitted-repo call sites


### FINDING_3: Bootstrap and finalize harnesses remain wired to deleted helpers
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan retargets admission tests but leaves bootstrap and finalize harnesses using deleted `get-issue-*` helper stubs and old log expectations. After call sites move to `python3 cli.py issue state|context|info`, offline cases can bypass stubs, hit real behavior, or fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mandate retargeting test-implement-bootstrap.sh and test-implement-finalize.sh with python3 stubs for issue state info context; update B6 B7 STEP_FAILED assertions to issue-state
  - From Codex-Pragmatic: Update the actual harnesses to intercept the new cli.py issue verbs in their existing dispatchers, or adjust gh stubs to return the JSON expected by issue_query.py
  - From Cursor-Requirements: Add explicit retarget steps for `skills/implement/scripts/test-implement-bootstrap.sh` and `scripts/test-implement-finalize.sh` (extend the existing `cli.py` dispatcher with `issue` verb stubs honoring the same env vars, update invoke-log assertions)


### FINDING_4: Prose blocker parser may lose bash regex parity
- **Reviewer(s)**: Codex-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The proposed prose blocker parser can diverge from bash parsing. Risks include matching across newlines and missing bash-specific boundaries or non-match cases, which can change admission blocker sets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Apply the regex per line or use whitespace that excludes CR/LF, and keep the concatenated/cross-line false-match test
  - From Cursor-Requirements: Port the bash regex boundaries (`([^0-9]|$)` after digits, preserved `[` for link-target NON-matches, strict spacing) and carry the high-signal NON-match fixtures from `scripts/test-parse-prose-blockers.sh` into `python/test_blocker.py`


### FINDING_5: Retired-script stale references may remain tracked
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan adds retired manifest rows but omits a bounded stale-reference sweep across tracked docs and lint config. Once retired scripts are recorded, `lint-retired-scripts` can fail on remaining references to deleted paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Include a bounded stale-reference sweep for these files, replacing retired script names with python cli verbs or removing obsolete agent-lint exclusions


### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/implement-bootstrap.sh:1004,1019 and scripts/implement-bootstrap-invoke.sh:107-108
- **Concern**: [SCOPE-REDUCTION] Plan renames STEP_FAILED from get-issue-state to issue-state. Scenario: implement-bootstrap-invoke.sh maps operator stderr only for STEP_FAILED=get-issue-state; test-implement-bootstrap.sh B6/B7 and test-implement-bootstrap-invoke.sh exit-2 cases assert the old token. Rename adds cross-file churn with no wire benefit
- **Proposed resolution**: Keep emitting STEP_FAILED=get-issue-state (swap only the underlying command). If renaming is required, add matching updates for implement-bootstrap-invoke.sh and both bootstrap harness files to the plan


### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/implement-bootstrap.sh:1000-1019; scripts/implement-bootstrap-invoke.sh:107-109
- **Concern**: [SCOPE-REDUCTION] Plan renames STEP_FAILED=get-issue-state to issue-state without updating the existing exit-2 consumer. Scenario: The wrapper misses its dedicated recovery message and falls through to the generic step=issue-state branch on issue-state failures
- **Proposed resolution**: Keep STEP_FAILED=get-issue-state while swapping the command, or update implement-bootstrap-invoke.sh plus its harness in the same change




### FINDING_1: Preserve empty repo fallback for issue state/info
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-output-contract-parity
- **Severity**: important
- **Concern**: `issue state` and `issue info` must omit `--repo` when `--repo` is not supplied and `gh.resolve_repo` returns `None`, matching the bash helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify that when --repo is omitted and resolve_repo returns None, gh wrappers omit --repo (same as empty REPO today)
  - From Cursor-Innovation: Port the numeric --issue validation and FAILED envelope for issue state; when repo is omitted and resolve_repo returns None call gh without --repo like the bash helpers; add harness cases for empty repo resolution
  - From Cursor-dyn-output-contract-parity: Specify: when `gh.resolve_repo` returns `None`, proceed with `repo=None` / omit `--repo` on the `gh issue view` call, matching bash.


### FINDING_2: Retarget bootstrap harness updates to skills/implement paths
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-output-contract-parity, Codex-dyn-harness-stub-gap
- **Severity**: important
- **Concern**: The plan targets nonexistent or inactive `scripts/test-implement-bootstrap*.sh` paths, while Makefile targets run `skills/implement/scripts/test-implement-bootstrap*.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the plan and relevant-checks mappings to retarget skills/implement/scripts/test-implement-bootstrap.sh and, only if needed, skills/implement/scripts/test-implement-bootstrap-invoke.sh; replace the helper-script stubs and assertions there with cli.py issue state|context intercepts.
  - From Cursor-Innovation: Retarget every harness bullet to skills/implement/scripts/test-implement-bootstrap.sh and skills/implement/scripts/test-implement-bootstrap-invoke.sh; mirror the same paths in relevant-checks.sh mappings
  - From Codex-Pragmatic: Update the plan and relevant-checks mappings to retarget skills/implement/scripts/test-implement-bootstrap.sh and skills/implement/scripts/test-implement-bootstrap-invoke.sh
  - From Codex-Requirements: Revise the plan to update skills/implement/scripts/test-implement-bootstrap.sh and skills/implement/scripts/test-implement-bootstrap-invoke.sh, plus their relevant-checks mappings, instead of the nonexistent scripts/test-implement-bootstrap*.sh paths.
  - From Codex-dyn-output-contract-parity: Change the plan to update `skills/implement/scripts/test-implement-bootstrap.sh` and `skills/implement/scripts/test-implement-bootstrap-invoke.sh`, and map those paths in `scripts/relevant-checks.sh`.
  - From Codex-dyn-harness-stub-gap: Retarget the plan sections and relevant-checks mappings to skills/implement/scripts/test-implement-bootstrap.sh and skills/implement/scripts/test-implement-bootstrap-invoke.sh


### FINDING_4: Preserve issue state validation and two-line failure envelope
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-output-contract-parity, Codex-dyn-output-contract-parity
- **Severity**: important
- **Concern**: `issue state` must preserve bash validation, exit behavior, and separate `FAILED` / `ERROR` KV lines so bootstrap parsing remains compatible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Port the numeric --issue validation and FAILED envelope for issue state; when repo is omitted and resolve_repo returns None call gh without --repo like the bash helpers; add harness cases for empty repo resolution
  - From Cursor-dyn-output-contract-parity: Port the `get-issue-state.sh` validation matrix into the plan and pytest: separate `emit_kv` lines, exact `ERROR=` tokens (`--issue is required`, `--issue must be numeric`, `gh issue view failed: …`), exit 1.
  - From Cursor-dyn-output-contract-parity: Require two `emit_kv` lines on failure; add a subprocess test asserting `FAILED` parses as exactly `true`.
  - From Codex-dyn-output-contract-parity: Specify and test two emitted lines: `FAILED=true` then `ERROR=<single-line message>`, with no spaces around `=` and exit 1.


### FINDING_6: Keep backtick stripping newline-safe
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: Whole-text backtick stripping can consume across newlines and change blocker detection compared with the line-local bash path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Strip inline backtick spans per line, or use a newline-safe pattern such as r'`[^`\n]*`' before matching each line. Keep parity with scripts/parse-prose-blockers.sh:45-50.
  - From Codex-Pragmatic: Apply backtick stripping per line, or use a regex that cannot consume newline characters before matching


### FINDING_9: Preserve issue context validation and exit codes
- **Reviewer(s)**: Cursor-dyn-output-contract-parity, Codex-dyn-output-contract-parity
- **Severity**: important
- **Concern**: `issue context` must preserve bash validation and exit-code distinctions, including exit 2 for usage/validation failures and exit 1 for GitHub read/runtime failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-output-contract-parity: Match bash: `--issue` must match `^[1-9][0-9]*$`; keep exit 2 for argv/validation failures and exit 1 only for gh/write failures; add pytest/fixture coverage.
  - From Codex-dyn-output-contract-parity: Preserve exit 2 for argument and validation failures, and use exit 1 for GitHub read or runtime failures.


### FINDING_12: Map admission blocker cases to STUB_BLOCKERS
- **Reviewer(s)**: Cursor-dyn-harness-stub-gap
- **Severity**: important
- **Concern**: Removing `gh api` blocked-by arms without setting `STUB_BLOCKERS` per admission case may make blocker scenarios return success instead of the expected block exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-stub-gap: List per-case STUB_BLOCKERS values (77, 99, 88) including the inline prose-blocker-blockers-kv invocation




### FINDING_4: Markdown link-text blocker parity is underspecified
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: Parser parity may preserve markdown link-target non-matches while dropping the existing positive fixture where `keyword+#N` appears inside markdown link text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit parity bullet: bracket before # stays a non-match; keyword+#N inside link text still matches; port both fixtures from scripts/test-parse-prose-blockers.sh
  - From Cursor-Requirements: Clarify that `Depends on [#150](url)` stays a non-match while `[Depends on #150](url)` must still match; add the positive link-text fixture to `python/test_blocker.py` coverage
  - From Codex-Requirements: Add the existing `keyword+#N inside link text` fixture to `python/test_blocker.py` parser parity tests


### FINDING_6: Planned blocker code crosses a private gh.py boundary
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: Calling private `gh._loads_json_paginated_list` from `blocker.py` can violate `reportPrivateUsage=error` and fail `make py-lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Expose a public paginated-list parser or keep native blocked-by parsing behind a public gh.py helper
  - From Codex-Pragmatic: Expose a public paginated JSON helper in gh.py and call that, or parse the paginated arrays inside blocker.py without importing an underscore helper


### FINDING_7: Final validation omits make lint
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The testing strategy omits required `make lint` validation even though the definition of done requires `make lint + py-lint + py-test` green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add `make lint` to the final testing strategy


### FINDING_8: Native blocker tests may miss paginated output coverage
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan switches native blockers to raw paginated JSON but does not require a test proving blockers on later concatenated pages are included.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a `native_open_blockers` test with concatenated array pages, including an open blocker only on the later page


### FINDING_9: IS_PR output casing may break bootstrap guard
- **Reviewer(s)**: Codex-dyn-output-contract-drift
- **Severity**: important
- **Concern**: The issue state plan does not require lowercase `IS_PR=true|false`, so Python bool output like `IS_PR=True` may bypass consumers that compare to literal `true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-output-contract-drift: Specify and emit IS_PR=true or IS_PR=false exactly. Convert the Python bool with an explicit lowercase helper, and keep bootstrap stubs using the same casing.


### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/test-implement-bootstrap.sh:262-274
- **Concern**: [SCOPE-REDUCTION] Bootstrap harness is asked to prove issue_query repo-omission internals. Scenario: The shell harness will either duplicate python/test_issue_query.py or add brittle real-CLI stubbing beyond the call-site cutover
- **Proposed resolution**: Remove that bootstrap-harness assertion and keep the omitted-repo coverage in python/test_issue_query.py


### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/test-implement-bootstrap.sh:104-123; scripts/test-implement-finalize.sh:135-154; plan.txt:512-529,561-569
- **Concern**: [SCOPE-REDUCTION] Bootstrap/finalize harness plan adds PATH-level python3 stubs instead of extending the existing sandbox cli.py dispatcher. Scenario: A PATH python3 shim must re-dispatch existing session CLI calls and may mask unrelated Python invocations; these harnesses already have a narrower cli.py dispatcher seam
- **Proposed resolution**: Extend the existing sandbox python/cli.py dispatcher to intercept issue state/context/info and delegate other verbs to real-cli.py; do not add a separate python3 shim there


### FINDING_14:
- **Reviewer(s)**: Codex-dyn-harness-stub-completeness
- **Severity**: important
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:512-537
- **Concern**: [SCOPE-REDUCTION] Bootstrap harness plan adds internal CLI validation and repo-resolution coverage that the shell callsite cannot naturally exercise. Scenario: The planned python3 stub intercepts cli.py issue state/context, so it cannot also prove the real gh issue view omits --repo; the context exit-2 validation arm would be dead because implement-bootstrap always passes issue, repo, and tmpdir on that path
- **Proposed resolution**: Remove the bootstrap-harness omitted-repo assertion and the unused context validation-style exit-2 stub arm; keep those checks in python/test_issue_query.py, where the plan already covers them.




### FINDING_3: Intercept blocker CLI in admission harness
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-harness-intercept-completeness
- **Severity**: important
- **Concern**: The admission harness defines a `python3` stub but may not install it into each blocker case’s `PATH`. After cutover, blocker checks can invoke the real Python CLI and possibly real GitHub instead of the intended stubs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Wire make_python3_stub into make_gh_stub or every stub_dir setup before PATH export; assert the stub intercepts cli.py blocker all-open
  - From Cursor-dyn-harness-intercept-completeness: In the `scripts/test-implement-admission.sh` retarget section, require `make_python3_stub` run for every blocker-exercising `sd` (or fold it into `make_gh_stub`), with `PATH="$sd:$PATH"` unchanged.


### FINDING_4: Parse all paginated prose comment bodies
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Concern**: `prose_open_blockers` can miss blockers in comments if it feeds raw JSON rows into prose parsing or only reads one comment page. It must extract each comment `.body` across all paginated comment results before blocker state lookups.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mirror blocker-helpers.sh: parse issue body from title/body JSON then parse each comment's .body string separately before state lookups
  - From Codex-Innovation: In prose_open_blockers, parse issue_comments_list_read stdout with gh.loads_json_paginated_list and iterate every comment body. Add one python/test_blocker.py case with concatenated comment-page arrays where a later page contains the open blocker.


### FINDING_7: Preserve bootstrap context invoke logging
- **Reviewer(s)**: Cursor-dyn-harness-intercept-completeness
- **Severity**: important
- **Concern**: Bootstrap harness assertions may be retargeted to `cli.py issue context`, but the post-cutover dispatcher may not write the old `invoke-log.txt` signal. That can either fail GP3 or remove coverage that context fetching actually ran.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-intercept-completeness: Require the sandbox `cli.py` dispatcher to append an invoke-log line for intercepted `issue context`/`issue state` (mirroring old helper stubs), and retarget GP3’s assertion to that line; or explicitly drop the invoke-log check and rely on `upstream-context.out` only.


### FINDING_8: Match absolute cli.py paths in admission stub
- **Reviewer(s)**: Cursor-dyn-harness-intercept-completeness
- **Severity**: important
- **Concern**: The admission `python3` stub contract may only match a bare `cli.py` argument. Production invokes `python3` with an absolute path to `python/cli.py`, so a narrow matcher can delegate to the real CLI and network.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-intercept-completeness: Document stub matching on `*/cli.py` plus `blocker`/`all-open` in argv (or scan `"$*"`), not cwd-relative `cli.py` only.




### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/blocker.py:172-185, python/issue_query.py:288-354
- **Concern**: Plan mandates quiet_init for new CLIs but does not require KV output via logging_util.emit_kv / contract_stream. Scenario: After quiet_init, stdout is redirected to the quiet log; print() or sys.stdout.write for BLOCKERS=/STATE=/VALUE= goes to the log while implement-finalize.sh and implement-bootstrap.sh command substitution only captures FD 1 (FD 3 carries contract when quiet is active). Finalize rename and bootstrap state probes can see empty KV blocks despite successful gh reads.
- **Proposed resolution**: Add an explicit contract line: all machine-readable KV lines for blocker all-open and issue state|info|context must use logging_util.emit_kv (same pattern as python/clarify.py), never bare print to stdout.


### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/blocker.py:172-185, python/issue_query.py:288-354
- **Concern**: Plan requires quiet_init for new CLIs but not logging_util.emit_kv / contract_stream for KV output. Scenario: After quiet_init, stdout goes to the quiet log. Bare print() for BLOCKERS=/STATE=/VALUE= lands in the log, not in command-substitution capture. implement-finalize.sh and implement-bootstrap.sh can parse empty KV blocks while gh succeeded.
- **Proposed resolution**: Add an explicit contract: all machine-readable KV for blocker all-open and issue state|info|context must use logging_util.emit_kv (python/clarify.py pattern), never print to stdout.


### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-bootstrap.sh:478-496
- **Concern**: Bootstrap cutover hardcodes `${SCRIPT_DIR}/../python/cli.py` instead of existing `$PY_CLI`. Scenario: `implement-bootstrap.sh` already routes every other CLI call through `PY_CLI="$CLAUDE_PLUGIN_ROOT/python/cli.py"` (line 26). When `CLAUDE_PLUGIN_ROOT` is set to a plugin cache or sparse checkout that is not `SCRIPT_DIR/..`, the new `issue context` / `issue state` calls can invoke a different `cli.py` than the rest of Step 0.
- **Proposed resolution**: Follow the file's existing convention: call `python3 "$PY_CLI" issue context|state ...` for both cutover sites.


### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-bash-contract-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/issue_query.py:294-315
- **Concern**: The `issue state` CLI spec lists five validation errors but omits the flag-looking-next-token guards in `get-issue-state.sh` (`case "$2" in --*)` for both `--issue` and `--repo`).. Scenario: `scripts/get-issue-state.sh` rejects `--issue --repo upstream/repo` and `--issue 12 --repo --flag` with `FAILED=true`, `ERROR=--issue requires a value` or `ERROR=--repo requires a value`, and exit 1 (`scripts/test-get-issue-state.sh` cases j/k). The plan’s pytest checklist (`python/test_issue_query.py` lines 381-382) does not require those cases; a naive `argparse` port can accept flag tokens as values and break the stated “port the bash validation matrix” contract.
- **Proposed resolution**: Extend the `issue state` CLI validation spec and pytest list to include flag-looking value rejection for `--issue` and `--repo`, matching `scripts/get-issue-state.sh:43-45` and `53-55`.


### FINDING_8:
- **Reviewer(s)**: Codex-dyn-bash-contract-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/get-issue-context.sh:17-24
- **Concern**: Planned issue context validation gives missing flag values exit 2, but the retired helper exits 1 before usage. Scenario: The plan says missing flag values exit 2; bash uses ${2:?--issue requires a value} under set -euo pipefail for --issue, --repo, and --tmpdir, so a final missing value exits 1 with no TITLE_FILE/BODY_FILE envelope
- **Proposed resolution**: Change the plan and tests to pin exit 1 with no KV stdout for final missing flag values, or explicitly mark this as an intentional non-parity change instead of preserved bash behavior


### FINDING_9:
- **Reviewer(s)**: Codex-dyn-bash-contract-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/get-issue-info.sh:25-37
- **Concern**: [SCOPE-REDUCTION] Planned issue info fail-open contract is broader than the retired helper for flag values with no argument. Scenario: The plan says VALUE= on missing required args and exit 0 always, but --issue, --field, or --repo without a following value exits 1 before the missing-arg VALUE= path runs
- **Proposed resolution**: Limit VALUE=/exit 0 to absent required args, invalid field, invalid flag, and gh failures; specify exit 1 with no VALUE= for final missing flag values if preserving actual helper parity


### FINDING_10:
- **Reviewer(s)**: Codex-dyn-harness-intercept-gap
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/migrated-scripts.tsv:1-12
- **Concern**: Plan scopes migrated-scripts rows to deleted bash helpers and harnesses only, but the Deleted list also removes sibling .md contracts; the retired-script manifest contract takes full repo-relative paths and current migration rows include .md contract paths.. Scenario: Deleted docs such as scripts/blocker-helpers.md and scripts/get-issue-state.md would not be recorded in the manifest, so lint retired-scripts cannot catch those retired files or same-path references after the sweep.
- **Proposed resolution**: Update the plan's python/migrated-scripts.tsv step to append rows for every path in the Deleted block, including all .md contract and harness docs.



