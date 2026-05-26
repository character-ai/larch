### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-7a.sh:444-478
- **Concern**: Plan Item A §2 mislabels diagram-rejected and diagram-failure as empty-SKIP_REASON fallback cases. Scenario: The rejected stub always prints SKIP_REASON (default pipe-in-node-label fence=mermaid line=7; failed default helper-error). After wiring kv_value into step-7a, assertions that still expect Code flow diagram not available. will fail and edge-case #1 prose is wrong
- **Proposed resolution**: Add diagram-rejected (baseline) to Item A assertion updates; expect token-only or full stub value consistently; change diagram-failure assertion to helper-error (or empty stub) not the generic placeholder


### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-failed-jobs.sh:106-108
- **Concern**: Sanitization is planned after the non-empty guard. Scenario: An all-control-byte job name passes the first guard, is stripped to empty, increments FAILED_JOBS_COUNT, and can emit an empty malformed TSV/unfixable record despite the plan claiming the guard skips it
- **Proposed resolution**: Sanitize raw_name before the non-empty guard or add a second guard immediately after sanitization; add an all-control-byte fixture


### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-7a.sh:131-139,444-478
- **Concern**: The Step 7a assertion plan is inconsistent with the harness stubs. Scenario: The plan says baseline diagram-rejected and diagram-failure should keep the placeholder when no SKIP_REASON fixture is set, but the stub always emits default SKIP_REASON values, so Item A will change those summaries and the kept assertions will fail
- **Proposed resolution**: Either make the stub emit empty SKIP_REASON when the env var is unset and add explicit SKIP_REASON cases, or update the baseline assertions to the default tokens and add separate empty-SKIP_REASON fallback cases


### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/lib-quiet.sh:98-104, scripts/test-lib-quiet.sh:132-139
- **Concern**: The shared larch_err behavior change is not covered at the integration point. Scenario: A helper-only test can pass while larch_err still leaks controls, writes sanitized text to stdout because of pipeline redirection, or breaks quiet FD4 stderr routing
- **Proposed resolution**: Extend the existing larch_err test to call larch_err with BEL/ESC in quiet and non-quiet modes, asserting stdout remains contract-only and stderr contains printable text with controls stripped


### FINDING_5:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-failed-jobs.sh:106-108
- **Concern**: Sanitize runs after the only empty-name guard. Scenario: An all-control-byte gh job name passes `[ -n "$raw_name" ]`, sanitizes to empty, still increments `count` and can emit a blank TSV/`emit` row; Edge cases §2 wrongly claims line 107 catches this
- **Proposed resolution**: Sanitize first then `[ -n "$raw_name" ] || continue`, or repeat the empty guard immediately after assignment


### FINDING_6:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:98-103
- **Concern**: The larch_err replacement text does not group the sanitized pipeline with the stderr redirection. Scenario: Applying the plan literally sends the sanitized message to stdout or the quiet log and redirects only the trailing newline to FD 4 or stderr, so user-visible diagnostics become blank or leak onto stdout
- **Proposed resolution**: Wrap the pipeline and newline in a redirected group for each branch, e.g. { printf '%s' "$*" | sanitize_diagnostic_line; printf '\n'; } >&4 and the same group redirected to >&2


### FINDING_7:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-failed-jobs.sh:106-110
- **Concern**: The plan sanitizes raw_name after the existing non-empty guard but does not add a second guard. Scenario: An all-control-byte job name passes the first guard, is sanitized to empty, increments FAILED_JOBS_COUNT, and can emit an empty TSV job field plus an =malformed-job-name tuple
- **Proposed resolution**: Add [ -n "$raw_name" ] || continue immediately after raw_name=$(printf '%s' "$raw_name" | sanitize_diagnostic_line) and before count=$((count + 1))


### FINDING_8:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-7a.sh:126-135,444-467
- **Concern**: The baseline diagram-rejected case is treated as an empty-SKIP_REASON fallback in the plan, but the stub always emits a SKIP_REASON in rejected mode. Scenario: After Item A, diagram-rejected will write pipe-in-node-label fence=mermaid line=7 to summary-diagrams.md, so keeping the placeholder assertion makes the harness fail
- **Proposed resolution**: Update the baseline diagram-rejected assertion to expect the stub's default SKIP_REASON, or add an explicit rejected-mode fixture that emits SKIP_REASON= when testing the fallback path


### FINDING_9:
- **Reviewer(s)**: Codex-Edge
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-7a.md:11-14
- **Concern**: The ledger reconciliation leaves stale descriptions saying sanitizer rejections skip summary upsert. Scenario: The harness asserts tracking-issue-summary.sh is called for rejected cases, so the md ledger remains misleading after the proposed rename pass
- **Proposed resolution**: Change those descriptions to say the placeholder or SKIP_REASON summary comment is posted, matching test-step-7a.sh assertions


### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:98-103
- **Concern**: The larch_err edit is specified as a semicolon-separated replacement while "keeping FD redirection unchanged", which can redirect only the trailing newline to FD 4 or stderr and leave the sanitized payload on stdout.. Scenario: In quiet mode, a user-visible diagnostic can pollute the machine-readable contract stream, breaking callers that parse emit and emit_kv output; it also defeats the intended stderr-only sanitization boundary.
- **Proposed resolution**: Make the plan require explicit grouping or pipeline redirection, e.g. { printf '%s' "$*" | sanitize_diagnostic_line; printf '\n'; } >&4 and the same group >&2 in the else branch.


### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-failed-jobs.sh:106-108
- **Concern**: The plan sanitizes raw_name after the existing non-empty guard but then claims all-control-byte names are skipped by that guard. A name containing only control bytes is non-empty before sanitization and empty afterward.. Scenario: Such a job line increments FAILED_JOBS_COUNT and can emit an empty job field or an =malformed-job-name tuple instead of being dropped, contradicting the proposed edge-case behavior and producing malformed TSV/KV output.
- **Proposed resolution**: Sanitize before the non-empty guard, or add a second [ -n "$raw_name" ] || continue immediately after sanitization before count is incremented.


### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-step-7a.sh:126-139,444-479
- **Concern**: The assertion-update plan treats baseline diagram-rejected and diagram-failure as empty-SKIP_REASON fallback cases, but the current test generator stub always emits a non-empty SKIP_REASON for both rejected and failed modes.. Scenario: After Step 7a starts honoring SKIP_REASON, those unchanged placeholder assertions will fail; if the stub is altered ad hoc, the harness may stop covering the real generator contract where sanitizer rejections and ordinary failures emit reason tokens.
- **Proposed resolution**: Revise the plan so baseline rejected expects "pipe-in-node-label fence=mermaid line=7" and baseline failed expects "helper-error", or explicitly change the stub to support a separate empty-SKIP_REASON fallback mode and add/update cases around that behavior.


### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:98-103
- **Concern**: The proposed larch_err replacement is a two-command pipeline/list but the plan says to keep the existing redirection unchanged without grouping it.. Scenario: If implemented literally as printf '%s' "$*" | sanitize_diagnostic_line; printf '\n' >&4, the diagnostic text goes to current stdout or the quiet log and only the newline reaches original stderr, hiding usage/fatal messages.
- **Proposed resolution**: Specify grouped redirection, e.g. { printf '%s' "$*" | sanitize_diagnostic_line; printf '\n'; } >&4 and the same form for >&2.


### FINDING_15:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lib-quiet.sh:98-103; scripts/git-force-push.sh:67-72
- **Concern**: Global larch_err sanitization with tr -d '[:cntrl:]' also strips embedded newlines and tabs, but existing callers pass multi-line diagnostics such as git status porcelain output.. Scenario: A dirty worktree with multiple files would be reported as one concatenated line, making push/PR safety errors harder to understand and breaking existing diagnostic behavior outside the ci-failed-jobs scope.
- **Proposed resolution**: Either sanitize only the ci-failed-jobs external content at the caller, or make larch_err preserve LF boundaries by sanitizing each line separately and consider preserving tabs if current tests or diagnostics rely on them.


### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-failed-jobs.sh:106-108
- **Concern**: The plan sanitizes raw_name after the existing non-empty guard, then assumes that same guard will skip all-control-byte names.. Scenario: A gh job name made only of control bytes passes the pre-sanitize guard, becomes empty, increments FAILED_JOBS_COUNT, and can emit an empty TSV job field plus malformed unfixable tuple.
- **Proposed resolution**: Sanitize before the non-empty check, or add a second [ -n "$raw_name" ] || continue immediately after sanitization and before count increments; add the all-control-byte case to the new harness test.


### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-7a.sh:126-139; skills/implement/scripts/test-step-7a.sh:444-490
- **Concern**: The plan says to keep placeholder assertions for diagram-rejected and diagram-failure because they do not fixture SKIP_REASON, but the stub emits SKIP_REASON for both modes by default.. Scenario: After step-7a starts honoring SKIP_REASON, diagram-rejected will summarize pipe-in-node-label fence=mermaid line=7 and diagram-failure will summarize helper-error, so the planned unchanged placeholder assertions will fail.
- **Proposed resolution**: Update every existing case whose stub emits SKIP_REASON, including baseline diagram-rejected and diagram-failure, or change the stub to emit an empty SKIP_REASON for a dedicated fallback case.


### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/test-step-7a.md:11-16
- **Concern**: The md reconciliation only calls out the sanitizer-failure description, but several listed cases still say sanitizer rejection skips summary upsert or posts the old placeholder.. Scenario: The ledger remains misleading after the proposed behavior, while the harness asserts tracking-issue-summary.sh is called and Item A changes SKIP_REASON-bearing summaries away from the generic placeholder.
- **Proposed resolution**: Revise the rejected and failure descriptions while renaming the labels so the md matches the harness outcomes and the new SKIP_REASON behavior.


### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-7a.sh:444-478
- **Concern**: Plan keeps placeholder assertions for diagram-rejected and diagram-failure as empty-SKIP_REASON fallbacks. Scenario: Rejected stub always emits SKIP_REASON (default token+fence or helper-error); failed stub always emits helper-error; Item A wiring makes harness fail or leaves false-green assertions
- **Proposed resolution**: Update plan test-step-7a.sh edits: diagram-rejected baseline expects default stub SKIP_REASON; diagram-rejected-$token expects $token fence=mermaid line=7; diagram-failure expects helper-error; reserve placeholder only for generator-crash / empty-SKIP_REASON paths


### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-7a.sh:126-139,444-478
- **Concern**: Finding 1: Plan misses existing SKIP_REASON-emitting Step 7a cases. Scenario: The rejected stub always emits SKIP_REASON with a default token and the failed stub emits helper-error by default, so keeping placeholder assertions for diagram-rejected and diagram-failure will fail after Item A and under-test the new contract
- **Proposed resolution**: Update the plan to change diagram-rejected to expect pipe-in-node-label fence=mermaid line=7 and diagram-failure to expect helper-error, or change the stub to emit empty SKIP_REASON for explicit fallback-only cases and add separate non-empty SKIP_REASON assertions


### FINDING_21:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-failed-jobs.sh:106-110
- **Concern**: Finding 2: All-control-byte job-name edge case is not actually handled. Scenario: The plan sanitizes raw_name after the existing non-empty guard, so a gh job name containing only control bytes becomes empty after the guard, increments FAILED_JOBS_COUNT, and can emit an empty malformed TSV row instead of being skipped as the plan claims
- **Proposed resolution**: Add a second [ -n "$raw_name" ] || continue immediately after raw_name=$(printf '%s' "$raw_name" | sanitize_diagnostic_line) and before count=$((count + 1))


### FINDING_22:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lib-quiet.sh:98-103
- **Concern**: Finding 3: larch_err replacement lacks explicit grouped redirection. Scenario: The literal replacement printf '%s' "$*" | sanitize_diagnostic_line; printf '\n' while keeping the old trailing redirection can redirect only the newline to FD 4 or stderr, leaving the sanitized diagnostic on stdout or the quiet log
- **Proposed resolution**: Add an explicit grouped command in the plan, e.g. { printf '%s' "$*" | sanitize_diagnostic_line; printf '\n'; } >&4 and the corresponding >&2 branch, and keep the existing larch_err stderr test as validation


### FINDING_23:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-mermaid-fragments.sh:223-237
- **Concern**: Finding 4: Item C lacks direct validation for embedded equals in warning aggregation. Scenario: The plan changes sanitize-mermaid-fragment.sh specifically to preserve embedded = in REASON_TOKEN aggregation, but no test update exercises that parser path; current fixtures only cover tokens without =
- **Proposed resolution**: Add a focused scripts/test-mermaid-fragments.sh assertion using a synthetic reasons file or equivalent helper around the warning-token awk expression so token values like future=token are preserved in the appended Warnings entry, and include bash scripts/test-mermaid-fragments.sh in the targeted test list


### FINDING_24:
- **Reviewer(s)**: Cursor-dyn-kv-contract-tracer
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:141-144
- **Concern**: Item A harness section omits diagram-rejected baseline and diagram-failure assertion updates while edge case #1 claims they still test empty SKIP_REASON fallback. Scenario: After kv_value wiring the stub always emits non-empty SKIP_REASON on rejected (test-step-7a.sh:134) and failed (test-step-7a.sh:138 default helper-error); keeping placeholder assertions at test-step-7a.sh:455 and :478 will fail CI or force a partial implementation
- **Proposed resolution**: Add diagram-rejected (line 455) and diagram-failure (line 478) to the assertion-update list; diagram-rejected baseline should expect pipe-in-node-label fence=mermaid line=7 or align the stub first; diagram-failure should expect helper-error


### FINDING_25:
- **Reviewer(s)**: Cursor-dyn-kv-contract-tracer
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:183-184
- **Concern**: Edge case #1 mislabels diagram-rejected as testing empty SKIP_REASON when STEP7A_GEN_FORCE_SKIP_REASON is unset. Scenario: Implementers may skip required assertion updates believing the baseline still covers fallback; only generator-crash (empty stdout, test-step-7a.sh:140-142) truly exercises the wildcard/placeholder path
- **Proposed resolution**: Rewrite edge case #1 to name generator-crash (and any new stub mode with SKIP_REASON=) as the empty-reason cases; remove diagram-rejected from the empty-SKIP_REASON list


### FINDING_29:
- **Reviewer(s)**: Codex-dyn-kv-contract-tracer
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:141-145; skills/implement/scripts/test-step-7a.sh:131-138,444-478
- **Concern**: Plan preserves placeholder assertions for cases whose stub already emits SKIP_REASON. Scenario: After step-7a honors SKIP_REASON, diagram-rejected writes pipe-in-node-label fence=mermaid line=7 and diagram-failure writes helper-error, so the harness will fail if those assertions keep expecting Code flow diagram not available.
- **Proposed resolution**: Update baseline diagram-rejected and diagram-failure assertions to the emitted SKIP_REASON, or change the stub to emit SKIP_REASON= for fallback cases and add separate explicit fallback coverage.


### FINDING_30:
- **Reviewer(s)**: Codex-dyn-kv-contract-tracer
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-7a.md:50-52
- **Concern**: Step 7a contract doc remains aligned to placeholder-only skipped failed summaries. Scenario: The proposed runtime behavior can upsert the generator SKIP_REASON token instead of the literal placeholder, leaving the sibling contract misleading after the PR lands.
- **Proposed resolution**: Add step-7a.md to the plan and document skipped/failed summaries as generator SKIP_REASON when present, falling back to Code flow diagram not available.


### FINDING_31:
- **Reviewer(s)**: Cursor-dyn-harness-drift-auditor
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:141-144 / skills/implement/scripts/test-step-7a.sh:131-134,457-467
- **Concern**: Item A coupling cites STEP7A_GEN_FORCE_SKIP_REASON for diagram-rejected-<token> loop; harness sets STEP7A_SANITIZER_TOKEN inside the for-loop (457-460) and the stub builds SKIP_REASON as "${token} fence=mermaid line=7" (134). Scenario: Implementer searches only STEP7A_GEN_FORCE_SKIP_REASON, misses loop updates, or asserts wrong strings (token only vs token+fence suffix)
- **Proposed resolution**: Rename fixture to STEP7A_SANITIZER_TOKEN; assert placeholder_expected_summary "${sanitizer_token} fence=mermaid line=7" per iteration; note loop sets env per iteration (not once outside)


### FINDING_32:
- **Reviewer(s)**: Codex-dyn-harness-drift-auditor
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-7a.sh:131-135,444-455
- **Concern**: Plan says diagram-rejected baseline should keep the placeholder assertion because it does not fixture SKIP_REASON, but the rejected stub always emits SKIP_REASON using STEP7A_SANITIZER_TOKEN default pipe-in-node-label.. Scenario: After the proposed step-7a SKIP_REASON wiring, diagram-rejected will write pipe-in-node-label fence=mermaid line=7 into the summary, so the planned placeholder assertion will fail and this case will not test the empty-SKIP_REASON fallback.
- **Proposed resolution**: Revise Item A/B coupling to either update diagram-rejected to expect pipe-in-node-label fence=mermaid line=7 or change the fixture so baseline rejected emits an empty SKIP_REASON if it is meant to cover fallback.


### FINDING_33:
- **Reviewer(s)**: Codex-dyn-harness-drift-auditor
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-7a.sh:136-139,470-479
- **Concern**: Plan says diagram-failure can keep the placeholder assertion if it does not fixture SKIP_REASON, but the failed stub always emits SKIP_REASON with default helper-error when STEP7A_GEN_FORCE_SKIP_REASON is unset.. Scenario: After the proposed step-7a failed-branch change, diagram-failure will use helper-error instead of Code flow diagram not available., so the planned assertion strategy misses another non-empty SKIP_REASON case.
- **Proposed resolution**: Revise Item A/B coupling to explicitly name diagram-failure and update its assertion to helper-error, or alter the failed fixture to emit an empty SKIP_REASON for this case and add a separate helper-error case if needed.


### FINDING_34:
- **Reviewer(s)**: Cursor-dyn-sanitizer-byte-scope
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-failed-jobs.sh:106-108
- **Concern**: Post-sanitize empty job_name not skipped. Scenario: Item D places sanitize after the line-107 `[ -n "$raw_name" ] || continue` guard; Edge cases #2 claims that guard catches all-control-byte names after strip, but it runs before sanitize — stripped names still increment count and can emit empty TSV/KV fields
- **Proposed resolution**: Re-run `[ -n "$raw_name" ] || continue` immediately after the sanitize assignment, or move sanitize before the first guard


### FINDING_35:
- **Reviewer(s)**: Codex-dyn-sanitizer-byte-scope
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:21; scripts/lib-quiet.sh:98-103
- **Concern**: Finding 1: larch_err edit spec replaces one redirected command with two commands but does not explicitly group the redirection. Scenario: If implementer keeps the original trailing >&4 or >&2 on only the second printf, the sanitized diagnostic text from printf pipe sanitize_diagnostic_line goes to current stdout or the quiet log while only the newline reaches stderr
- **Proposed resolution**: Specify the exact grouped form in both branches: { printf '%s' "$*" | sanitize_diagnostic_line; printf '\n'; } >&4 and the analogous >&2 branch, or capture sanitized output before one redirected printf


### FINDING_36:
- **Reviewer(s)**: Codex-dyn-sanitizer-byte-scope
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:31-35; <TMPDIR>/plan.txt:185; scripts/ci-failed-jobs.sh:106-110
- **Concern**: Finding 2: all-control-byte job_name skip logic is ordered incorrectly in the proposed edit. Scenario: The plan says the existing nonempty guard catches an all-control-byte name, but the proposed sanitize line is after that guard, so sanitization can turn raw_name empty after count increments and before job_name assignment, producing an empty TSV job field and malformed bookkeeping instead of skipping
- **Proposed resolution**: Move sanitization before the nonempty guard, or add a second [ -n "$raw_name" ] || continue immediately after sanitization and before count increments; add the planned ci-failed-jobs fixture with an all-control-byte job name


### FINDING_37:
- **Reviewer(s)**: Codex-dyn-sanitizer-byte-scope
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:147-152; <TMPDIR>/plan.txt:205-213; scripts/test-lib-quiet.sh:132-139; scripts/test-ci-failed-jobs.sh:174-194
- **Concern**: Finding 3: test plan verifies the helper but not larch_err routing through the helper. Scenario: A patch could add sanitize_diagnostic_line and pass the new helper unit test while leaving larch_err unsanitized or misdirected; the existing ci-failed-jobs failure test still sanitizes through the explicit line 86 pipe, so it would not prove the shared larch_err behavior
- **Proposed resolution**: Item E coverage should extend the existing larch_err test to pass BEL or ESC through larch_err, assert original stderr contains the sanitized prose and no control byte, and assert stdout contract output is unchanged before relying on Item D behavior


