### FINDING_1: Parse-rate CLI cutover lacks a complete argv contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The parse-rate retry/check/diagnostic cutover does not fully replace the current `LARCH_VPR_*` globals with an explicit, argv-safe CLI contract. This can drop required dispatch context, misparse option-shaped `--ctx` values, or silently change retry behavior across code and plan voters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Spell out the exact `VPR_ARGS` / per-slot flags that replace each `LARCH_VPR_*` global and require `python/test_voting.py` cases for code vs plan dispatch shapes.
  - From Cursor-Innovation: Add an explicit argv table for `voting parse-rate-check`, `parse-rate-retry`, and `parse-rate-diag-matches` mapping each current `LARCH_VPR_*` input and show the exact `dispatch-*-voters.sh` call pattern per slot
  - From Codex-Pragmatic: Specify an argv-safe encoding, for example --ctx=--diff-file --ctx "$bounded_diff" --ctx=--plan-file --ctx "$bounded_plan", and parse ctx values without treating leading dashes as voting options


### FINDING_2: Regex CLI substitutions can fail open in no-set-e validators
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Validator scripts that intentionally omit `set -e` may bind empty regex variables if the new CLI regex command fails. Empty grep patterns can then pass citation checks incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Fetch both regexes through an explicit checked helper in these no-set-e scripts, fail with the existing validator error path on nonzero or empty output, then use the fetched variables in the grep calls.


### FINDING_3: Write-tally command array cutover still invokes a single path
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan changes the default write-tally seam into a multi-word Python command but leaves callers and executability checks shaped for one executable path. The default tally flush can skip or fail after cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify `WRITE_TALLY_CMD` array wiring: default array, override env stays one executable, replace line 1054 with `"${WRITE_TALLY_CMD[@]}"`, and split the executability gate per the plan's override vs default rules


### FINDING_4: Judge-vote parser harnesses still target retired bash behavior
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Parser harness coverage still relies on the retired `parse-judge-vote-and-rating.sh` surface. After the Python CLI cutover, malicious-parser stubs and exit-matrix diagnostic assertions may no longer exercise the real parser path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Retarget the case to stub `$STUB_ROOT/python/cli.py` (or a `REVIEW_AND_FIX_WRITE_TALLY_SH`-style override) so the malicious KV fixture still drives `parse-judge-vote`; drop copies of deleted `lib-vote-tally.sh` / `parse-judge-vote-and-rating.sh`
  - From Cursor-Innovation: List every parser diagnostic assertion in both harnesses and pin the post-cutover `python/cli.py voting parse-judge-vote` stderr/usage strings (or relax checks to behavior: exit 2 on missing args/unreadable voter file)


### FINDING_6: Dispatch retry fixture still depends on retired bash voting libs
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The code-voter retry fixture still symlinks retired bash voting libraries and provides only a render-focused Python CLI stub. After deletion, parse-rate retry harness cases can fail without exercising the new Python voting verbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Extend the test-dispatch-code-voters.sh UPDATED row: copy real python/ (or execv to repo cli.py like test-dispatch-plan-voters.sh), drop symlinks to retired scripts, and ensure the sandbox cli exposes voting parse-rate-* verbs


### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:47-48,952,1054-1064
- **Concern**: [SCOPE-REDUCTION] Plan converts write-tally to a bash command array but leaves scalar WRITE_TALLY_SH invocation. Scenario: After cutover the default seam is `(python3 "$PLUGIN_ROOT/python/cli.py" voting write-tally)` while flush still runs `"$WRITE_TALLY_SH" --log-root ...` and gates on `[[ -x "$WRITE_TALLY_SH" ]]`. A multi-word default cannot execute; a single-path default skips the `python3` argv prefix. Step 5 tally flush silently returns at line 952 or fails at 1054.
- **Proposed resolution**: Name the override/default seams explicitly (e.g. `WRITE_TALLY_CMD` array vs `REVIEW_AND_FIX_WRITE_TALLY_SH` scalar). Gate override with `-x` and default with `test -f` on `python/cli.py`. Invoke `"${WRITE_TALLY_CMD[@]}"` (or the override scalar) at the flush site with the existing flags.


### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-deletion-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-dispatch-code-voters.sh:52-65,129-130
- **Concern**: [SCOPE-REDUCTION] Sandbox fixtures still stub a render-only cli.py and symlink retired parse-rate bash libs. Scenario: The plan only says copy the python/ tree. make_wait_barrier_plugin_root and make_voter1_delayed_done_plugin_root still write a cli.py that handles only render voter (lines 57-64, 133-140) and symlink lib-voter-parse-rate.sh and parse-judge-vote-and-rating.sh (129-130). After dispatch-code-voters.sh cuts over to voting parse-rate-* CLI calls, retry and happy-path sections that assert VOTER_*_PARSE_RATE_STATUS will hit exit 2 or miss diagnostics.
- **Proposed resolution**: Mirror scripts/test-dispatch-plan-voters.sh: execv shim to $REPO_ROOT/python/cli.py, copy required python/ modules and skills/shared deps, and delete the two retired-script symlinks from all sandbox builders.




### FINDING_2: parse-rate id grammar cutover can stop counting OOS ballot IDs
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Requirements, Cursor-dyn-argv-contract, Codex-dyn-argv-contract
- **Severity**: important
- **Concern**: The proposed `--id-grammar code|plan` contract can narrow the current `finding-oos` ballot scan and stop counting `OOS_N` headings, which can suppress retries, diagnostics, or `NOT_SUBSTANTIVE` handling for OOS-only voter outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Define both new domain labels as scanning FINDING_N and OOS_N, or keep the old finding-oos value at the CLI boundary.
  - From Codex-Innovation: Keep --id-grammar finding-only|finding-oos, or explicitly define both code and plan as counting FINDING_N plus OOS_N and pin that with one code and one plan OOS parse-rate case.
  - From Cursor-Requirements: Change the argv contract to `--id-grammar finding-only|finding-oos`. Have both dispatch scripts pass `--id-grammar finding-oos`. Keep ballot-kind distinction on `--retry-prefix-kind code|plan` only. Update `python/test_voting.py` fixtures accordingly.
  - From Cursor-dyn-argv-contract: Map `--id-grammar` to `finding-only|finding-oos`; cut over with `finding-oos` for both dispatchers; keep code/plan distinction on `--retry-prefix-kind` only
  - From Codex-dyn-argv-contract: Change --id-grammar to the existing grammar domain finding-only|finding-oos and pass finding-oos from both dispatchers; keep --retry-prefix-kind code|plan separate; document --launch-mode as the launcher mode value such as description


### FINDING_3: subprocess warning output can disappear into quiet logs
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Moving warning-emitting sourced helpers behind Python subprocess verbs can route diagnostics to quiet stderr while stdout is captured for machine parsing, hiding parse-rate and degraded-panel warnings from the operator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep stdout machine-only and add an explicit diagnostic route for parse-rate-* and degraded-warning, either by re-emitting warning text in the parent with larch_err or by using a tested Python helper that writes to the inherited fd4 without clobbering fd3.


### FINDING_4: parse-rate-retry stdout contract can break captured status values
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Dispatch captures `parse-rate-retry` stdout as a bare status token, but the plan only pins KV output for `parse-rate-check`, so emitting `PARSE_RATE_STATUS=...` can corrupt effective-judge math and degraded-panel handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document in the verb table that `parse-rate-retry` stdout is exactly one bare status line (same tokens as today). Add a pytest case and a dispatch harness assertion that captured value is `OK`/`NOT_SUBSTANTIVE`/… with no `=` prefix.
  - From Cursor-Pragmatic: Pin parse-rate-retry to print only OK or NOT_SUBSTANTIVE on stdout (no KV prefix), matching check_and_retry_voter_parse_rate; add pytest plus dispatch harness assertions on captured status tokens


### FINDING_5: code-review tally records can incorrectly include body text
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The `voting write-tally` plan omits the existing code-review contract that validates `--body-file` but does not include body content in `code-review-tally.json`, risking schema drift and duplicated rejected-findings prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: State that voting write-tally validates --body-file for code-review but never includes body in the record, and add a focused pytest for absent body on code-review with --body-file


### FINDING_6: parse-rate retry argv can forward empty optional context paths
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The planned `VPR_ARGS` cutover can append `--ctx=--diff-file` and `--ctx=--plan-file` unconditionally, forwarding empty option values on retry paths that currently omit missing optional context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Keep the existing [[ -n "$bounded_diff" ]] and [[ -n "$bounded_plan" ]] guards around the new --ctx entries in scripts/dispatch-code-voters.sh



### FINDING_1: Parse-rate harness suppression parity omitted
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan omits `should_suppress_parse_rate_issue_append` and `is_harness_review_path`, which currently prevent parse-rate warning paths from appending tool-failure issues during harness-shaped review runs. Porting without them can re-pollute parent `LARCH_EXECUTION_ISSUES_LOG` files and break dispatch voter isolation regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add those two helpers to the explicit parity contract (and a `python/test_voting.py` case) so `voting parse-rate-check` / `voting parse-rate-retry` preserve the current suppression behavior before `append-tool-failure.sh` runs.
  - From Cursor-Innovation: Port the harness-path predicate into parse-rate-check/retry; add pytest plus dispatch harness cases mirroring scripts/test-dispatch-code-voters.sh env-isolation assertions


### FINDING_4: parse-judge-vote failure fallback is not preserved
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The tally cutover does not require preserving the current `parse_vote_rating_for` failure behavior. Today non-zero judge parsing emits a warning breadcrumb and synthetic `JUDGE_ERROR` KV fields. A bare CLI substitution can drop diagnostics and change vote counts or classification inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Keep a thin bash wrapper or specify equivalent Python stderr/fd-3 diagnostic plus KV fallback in the tally-code-votes cutover steps
  - From Cursor-Pragmatic: Add an explicit tally-code-votes.sh step: on non-zero voting parse-judge-vote rc, keep the existing WARN>&3 breadcrumb and emit the same synthetic PARSED_* block (or document equivalent Python stdout on failure — today bash exits 2 without KV)


### FINDING_5: cutover snippets may expand unset variables under set -u
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Several proposed snippets use `CLI`, `DISPATCH_LABEL`, `LAUNCH_MODE`, or `PLUGIN_ROOT` without adding definitions in scripts that run under `set -u`. The cutover can abort before invoking the Python CLI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Define CLI from the existing root in each updated consumer, map DISPATCH_LABEL and LAUNCH_MODE from current literals or mode, and use PY_CLI or CLAUDE_PLUGIN_ROOT in implement-bootstrap instead of undefined PLUGIN_ROOT


### FINDING_6: degraded warning KV value contract is underspecified
- **Reviewer(s)**: Cursor-dyn-stdout-contract-fidelity
- **Severity**: important
- **Concern**: The degraded-warning verb row omits the exact `DEGRADED_PANEL_WARNING` value payload. The plan says prose should move to diagnostics, but existing behavior emits the banner string as a KV value, so the machine stdout contract is ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stdout-contract-fidelity: Specify the exact DEGRADED_PANEL_WARNING= value bytes after cutover, or keep the full banner string in the value for parity and narrow the harness wording to forbid extra non-KV stdout lines only


### FINDING_7: parse-rate retry exit-code parity is missing
- **Reviewer(s)**: Codex-dyn-stdout-contract-fidelity
- **Severity**: important
- **Concern**: The parse-rate retry contract omits the current source exit-code behavior. If Python propagates a nonzero launcher return code, dispatch command substitution under `set -e` can abort instead of capturing `NOT_SUBSTANTIVE`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-stdout-contract-fidelity: State that parse-rate-check and parse-rate-retry exit 0 whenever they emit OK or NOT_SUBSTANTIVE; retry launcher failure or empty retry output must clean retry temp files, keep original diag, print NOT_SUBSTANTIVE, and exit 0


### FINDING_8: plan voter coverage gates are incomplete
- **Reviewer(s)**: Codex-dyn-stdout-contract-fidelity
- **Severity**: important
- **Concern**: The voter-status-block and effective-judges contract omits gates for nonempty outputs and conditional `VOTER_PATHS_FILE` emission. All-failed or empty-output plan dispatch can count excluded judges or emit extra stdout keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-stdout-contract-fidelity: Add contract and tests: effective judge iff status != failed, parse status != NOT_SUBSTANTIVE, and path is nonempty with a nonempty file; status block emits VOTER_PATHS_FILE only when the paths file is nonempty, preserving both order variants


### FINDING_10: stale is_security_block test comment can fail retired-script lint
- **Reviewer(s)**: Cursor-dyn-cutover-completeness
- **Severity**: important
- **Concern**: The plan repoints assertions in `scripts/test-review-structure.sh` but does not require updating the nearby header comment that still names `scripts/lib-vote-tally.sh::is_security_block`. After deleting the retired script, the stale reference can trip `make lint-retired-scripts`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-cutover-completeness: Extend ### UPDATED: scripts/test-review-structure.sh to rewrite the (20) comment to cite python/voting.py (is_security_block) and grep python/voting.py instead of scripts/lib-vote-tally.md


### FINDING_11: stale file-line-regex markdown reference omitted
- **Reviewer(s)**: Codex-dyn-cutover-completeness
- **Severity**: important
- **Concern**: The stale-reference sweep omits `skills/implement/scripts/test-oos-file-conflict-deps.md`, which still names `scripts/file-line-regex-lib.sh`. Deleting that retired script can make `make lint-retired-scripts` fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-cutover-completeness: Add skills/implement/scripts/test-oos-file-conflict-deps.md to the stale-reference sweep and repoint line 12 to python/voting.py or voting file-line-regex


### FINDING_13:
- **Reviewer(s)**: Codex-dyn-stdout-contract-fidelity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/shared/scripts/scoreboard.sh:41, <TMPDIR>/plan.txt:43 and 616
- **Concern**: [SCOPE-REDUCTION] scoreboard contract changes path quoting from bash printf %q to shlex.quote. Scenario: SCOREBOARD_FILE value differs for output paths with spaces or shell metacharacters, so the Python verb is not byte-compatible with source
- **Proposed resolution**: Keep bash %q-compatible output for this migration, or remove the shlex.quote change from the B5 plan and track any quoting cleanup separately




### FINDING_1: Preserve skipped-slot parse-rate guards
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The dispatch-code-voters cutover can run parse-rate retry for skipped external slots, changing skipped defaults and effective-judge accounting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Preserve today's guards: initialize parse-rate status to SKIPPED, call parse-rate-retry only when VOTER_1_STATUS != failed and when VOTER_2/3_STATUS are not failed or skipped; keep the effective_judges loop's skipped exclusion
  - From Cursor-Pragmatic: Preserve the existing guards verbatim: slot 1 `!= failed`; slots 2/3 `!= failed && != skipped` before each `voting parse-rate-retry` call


### FINDING_5: Preserve parse-judge-vote edge semantics
- **Reviewer(s)**: Cursor-dyn-verb-contract-drift, Codex-dyn-verb-contract-drift
- **Severity**: important
- **Concern**: The parse-judge-vote contract can lose bash semantics for no-match or invalid votes, duplicate matches, EXONERATE mapping, axis parsing, and uncertainty reporting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-verb-contract-drift: Expand the verb row to match `scripts/parse-judge-vote-and-rating.md`: exit 0 with empty fields on no/invalid match; last-line-wins; `EXONERATE`→`NO`; axis parsing before ` -- `; `PARSED_UNCERTAIN=true` unless all four axes parse and `UNCERTAIN=false`.
  - From Codex-dyn-verb-contract-drift: Spell out case-insensitive anchored ID matching, last matching line wins, missing or unrecognized vote emits empty PARSED_VOTE with rc 0, EXONERATE maps to NO, axis tokens are enum-validated before optional " -- " delimiter, and PARSED_UNCERTAIN is true unless all four axes are valid


### FINDING_10: Preserve quiet-mode diagnostic routing
- **Reviewer(s)**: Cursor-dyn-stream-routing-consistency
- **Severity**: important
- **Concern**: Plain-stdout Python verbs can route diagnostics to stderr instead of inherited quiet fd 4, hiding operator-visible messages in quiet logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stream-routing-consistency: Pin diagnostic helpers: when LARCH_QUIET_ACTIVE is set and the child did not quiet_init, write sanitized prose with os.write(4, ...) (fallback to sys.stderr only when fd 4 is unavailable); keep machine tokens on stdout/fd 3 only


### FINDING_11: Keep write-tally stdout capture in review-and-fix
- **Reviewer(s)**: Codex-dyn-stream-routing-consistency
- **Severity**: important
- **Concern**: A bare write-tally invocation can leak larch-log key-value output into review-and-fix’s stdout contract stream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-stream-routing-consistency: Revise the review-and-fix cutover to keep the existing tally_out command substitution and rc capture around WRITE_TALLY_CMD, including stderr capture, and only relay captured output through larch_err on failure.




### FINDING_2: Invalid judge-vote tokens must preserve parsed axis fields
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-bash-contract-parity, Codex-dyn-bash-contract-parity
- **Severity**: important
- **Concern**: The plan changes invalid judge-vote semantics by clearing axis fields when the vote token is unrecognized. Current bash behavior preserves valid axis tokens on an anchored finding line while emitting an empty parsed vote. A Python port following the plan would regress forensic TSV data for malformed vote lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep current semantics: for an anchored ID match, reset fields, parse axis tokens before the rationale delimiter regardless of whether the vote token is recognized, emit only PARSED_VOTE empty for invalid votes, and preserve the existing axis-parses-with-unrecognized-vote assertion.
  - From Codex-Pragmatic: Revise parse-judge-vote contract and tests so only no-match clears axes; for a matching ID with an invalid vote token, keep enum-valid axis parsing before the delimiter while PARSED_VOTE stays empty
  - From Codex-Requirements: Revise the parse-judge-vote contract and tests to keep parsing valid axis tokens on a matched ID when the vote token is unrecognized, while PARSED_VOTE stays empty; reserve all-empty axis fields for no matching ID
  - From Cursor-dyn-bash-contract-parity: Align plan verb table, edge cases, and pytest/harness pins with `parse-judge-vote-and-rating.md`: no anchored ID line → empty vote and empty axis fields; anchored line with invalid/missing vote token → empty `PARSED_VOTE` only, axes still parsed from scoped text before ` -- `.
  - From Codex-dyn-bash-contract-parity: Revise python/voting.py and python/test_voting.py plan text so invalid vote leaves PARSED_VOTE empty but still applies the existing axis parser and PARSED_UNCERTAIN gating to the scoped pre-delimiter text


### FINDING_7:
- **Reviewer(s)**: Codex-dyn-bash-contract-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-vote-tally.sh:137-155
- **Concern**: [SCOPE-REDUCTION] Plan requires split-ballot duplicate detection before writes, but bash creates the output directory and writes each block as it scans before failing on a later duplicate. Scenario: Implementing a pre-scan or no-partial-writes guarantee adds behavior and complexity beyond the current migration contract for duplicate ballots
- **Proposed resolution**: Remove the before-writes/no-partial-writes requirement, or state that duplicate detection is streaming and may leave already-written block files just like split_ballot_to_blocks


