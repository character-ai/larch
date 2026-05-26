### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:102-103
- **Concern**: Approach claims no public output contract change but portable awk captures full post-prefix remainder. Scenario: Live sanitizer lines look like REASON_TOKEN=pipe-in-node-label fence=mermaid line=7; today SKIP_REASON is pipe-in-node-label fence (awk -F= field 2) and after the change becomes pipe-in-node-label fence=mermaid line=7 — silent KV drift for any log or test consumer of SKIP_REASON
- **Proposed resolution**: Revise Approach to document intentional SKIP_REASON widening, or narrow extraction (e.g. first whitespace-delimited token after REASON_TOKEN=) if only embedded-equals-in-token was intended; add harness case using the real sanitizer log line shape

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/ci-failed-jobs.sh:75-81
- **Concern**: Proposed stderr sanitization runs after read has already split on newline, so the newline-injection part of Item B remains unhandled. Scenario: A gh stderr payload containing attacker-controlled LF still produces multiple larch_err records before sanitize_diagnostic_line sees the data, allowing forged or confusing extra log lines
- **Proposed resolution**: Sanitize or encode tmp_stderr as a byte stream before line splitting, or intentionally collapse normalized stderr to a bounded single diagnostic record; update the regression to assert injected LF cannot create extra larch_err records

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/ci-failed-jobs.sh:25-27
- **Concern**: Proposed tr -d '[:cntrl:]' helper is locale-dependent rather than a deterministic byte sanitizer. Scenario: On macOS/BSD in a UTF-8 locale, malformed non-UTF-8 bytes from untrusted gh stderr can make tr report illegal byte sequence or produce inconsistent filtering
- **Proposed resolution**: Define the helper with LC_ALL=C tr -d '[:cntrl:]' and add a regression covering malformed high bytes plus valid UTF-8 pass-through

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/ci-failed-jobs.sh:79-81
- **Concern**: The proposed sanitizer runs after read has already split stderr on newlines, so it cannot prevent newline-driven log splitting. Scenario: A crafted gh stderr payload containing a newline still becomes multiple larch_err calls before sanitize_diagnostic_line sees it, contradicting the plan's stated newline hardening and the planned T8 assertion that injected newlines do not create extra logical log lines
- **Proposed resolution**: Sanitize the raw stderr stream before the read loop, or collapse/encode newline bytes before calling larch_err; update the test fixture to prove one crafted logical diagnostic with an embedded newline cannot produce extra emitted larch_err records

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/generate-code-flow-diagram.sh:102
- **Concern**: Proposed awk prints entire post-prefix remainder as SKIP_REASON. Scenario: Real sanitizer lines are REASON_TOKEN=<short-token> fence=N line=M (scripts/sanitize-mermaid-fragment.sh:201); fix changes SKIP_REASON from pipe-in-node-label fence to pipe-in-node-label fence=1 line=5, contradicting Approach no contract change and sanitize-mermaid-fragment.md short-token semantics
- **Proposed resolution**: Strip only the REASON_TOKEN= prefix then truncate at first space (sub(/ .*/,"")) so embedded = in the token is preserved but fence/line metadata stays out; add regression using production-shaped log line

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-failed-jobs.sh:79-81
- **Concern**: Newline stripping in sanitize_diagnostic_line is unreachable on the gh stderr path. Scenario: while IFS= read -r line splits tmp_stderr on newlines before sanitization runs, so embedded \n never appears in $line; T8 newline assertions would pass without the helper and do not prove the stated split-log-line mitigation
- **Proposed resolution**: Sanitize before line splitting (e.g., slurp tmp_stderr once, tr -d [:cntrl:], then read) or drop newline claims/tests and document that only intra-line control bytes are in scope

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-generate-code-flow-diagram.sh:35-60
- **Concern**: Item A test sketch invents write_sanitize_stub run_subject_skip_path assert_file_contains helpers absent from harness. Scenario: Harness uses inline SANITIZE_REJECT stub and assert_contains only; implementer may stall or duplicate scaffolding inconsistently
- **Proposed resolution**: Rewrite test sketch to extend existing SANITIZE_REJECT=1 path or add minimal helpers matching current assert_contains/pass/fail style

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-generate-code-flow-diagram.sh:77-82
- **Concern**: Regression case uses synthetic REASON_TOKEN=pipe-in-node-label=foo not production log shape. Scenario: Production rejects emit space-separated fence=/line= metadata; synthetic =foo case would pass while production-shaped lines still change SKIP_REASON under full-remainder awk
- **Proposed resolution**: Assert SKIP_REASON against a fixture mirroring sanitize-mermaid-fragment.sh output (token plus fence/line suffix) and expected short-token extraction

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/scripts/generate-code-flow-diagram.sh:102
- **Concern**: Plan rejects shared sanitizer despite identical parsing hazard elsewhere. Scenario: scripts/sanitize-mermaid-fragment.sh:283 uses a different awk idiom for token aggregation; future REASON_TOKEN values with = will diverge across consumers
- **Proposed resolution**: [OUT_OF_SCOPE] Track aligning token extraction in scripts/sanitize-mermaid-fragment.sh:283 or extracting one portable helper

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-generate-code-flow-diagram.sh:85
- **Concern**: Plan claims no-token fallback already covered. Scenario: Harness has no case asserting SKIP_REASON=sanitizer-rejected when REASON_TOKEN line is absent
- **Proposed resolution**: Add explicit fallback regression (sanitizer exits 1 without REASON_TOKEN= line)

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/test-ci-failed-jobs.sh:44-46
- **Concern**: T8 prose expects HTTP 500: Bad Gateway substring. Scenario: Existing GH_MODE=fail stub prints HTTP 500 only; prose/substring mismatch causes false-negative test design
- **Proposed resolution**: Align fixture text and assertions (extend fail mode or GH_FAIL_STDERR_FILE fixture)

### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-failed-jobs.sh:79-81
- **Concern**: Per-line sanitization happens after read has already split on newline. Scenario: The plan claims crafted embedded newlines cannot create extra logical log lines, but any LF in tmp_stderr is consumed as a record boundary before sanitize_diagnostic_line runs, so injected fragments still become separate larch_err records
- **Proposed resolution**: Frame each emitted diagnostic line with a fixed prefix or sanitize the stderr stream before line splitting; update the regression to assert every emitted record is framed and control-free

### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/ci-failed-jobs.sh:125-129
- **Concern**: Untrusted job names still reach TSV and emit output unsanitized. Scenario: The audit says only the stderr larch_err path takes untrusted external input, but successful gh output is also GitHub-controlled and malformed names containing control bytes are written to OUTPUT_TSV_TMP or emit before the final sanitize_list KV summaries
- **Proposed resolution**: Sanitize or replace malformed job names before any TSV/emit contract output, for example write a fixed malformed placeholder plus reason; add a success-path fixture with control bytes in job names

### FINDING_14:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/ci-failed-jobs.sh:25-29
- **Concern**: Proposed tr helper is locale-dependent on macOS/BSD. Scenario: In UTF-8 locales BSD tr can reject invalid byte sequences from untrusted stderr, producing its own diagnostic or dropping data unpredictably; the plan explicitly targets Bash 3.2/macOS portability
- **Proposed resolution**: Set LC_ALL=C for the helper, e.g. LC_ALL=C tr -d '[:cntrl:]', and add a fixture with invalid non-UTF-8 bytes

### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-generate-code-flow-diagram.sh:15-16,77-82
- **Concern**: Item A test sketch references helpers that do not exist in the harness. Scenario: The plan cites write_sanitize_stub, run_subject_skip_path, and assert_file_contains; the harness only defines assert_contains and drives rejection via SANITIZE_REJECT=1 on the inline sanitizer stub (lines 35-39, 50-53)
- **Proposed resolution**: Implement the regression by extending the existing stub (e.g. SANITIZE_REASON=pipe-in-node-label fence=1 line=7) and assert_contains on captured stdout, matching current patterns

### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/ci-failed-jobs.sh:79-80
- **Concern**: Proposed stderr sanitization runs after read has already split on LF and still forwards attacker-controlled fragments as standalone larch_err records. Scenario: A crafted gh stderr value containing a newline can still create an extra unprefixed diagnostic line that looks like an independent log record, so the newline-injection part of Item B remains unfixed
- **Proposed resolution**: Add a trusted fixed prefix at the larch_err call after sanitization, or sanitize/encode the raw stderr stream before line framing; update the T8 assertion to prove injected newline fragments cannot appear as standalone untrusted records

### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/ci-failed-jobs.sh:25-27
- **Concern**: Proposed tr -d '[:cntrl:]' helper is locale-dependent despite handling untrusted bytes. Scenario: On macOS/BSD tr under a UTF-8 locale, invalid byte sequences in gh stderr can produce tr diagnostics or truncated output, weakening the byte-safety contract
- **Proposed resolution**: Force byte-wise behavior in the helper, e.g. LC_ALL=C tr -d '[:cntrl:]' or an explicit C-locale octal range, and cover a non-UTF-8 byte fixture

### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-harness-api-fidelity
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/test-generate-code-flow-diagram.sh:35-53
- **Concern**: Plan says the existing harness covers the no-REASON_TOKEN fallback, but the current reject stub always emits REASON_TOKEN=test-reject. Scenario: A future edit could break the new END exit/fallback behavior without the claimed test catching it
- **Proposed resolution**: Add a small reject-without-token case asserting SKIP_REASON=sanitizer-rejected, or remove the inaccurate testing claim

### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-generate-code-flow-diagram.sh:15-62
- **Concern**: Plan test sketch calls write_sanitize_stub, run_subject_skip_path, and assert_file_contains APIs that do not exist in the harness. Scenario: Implementer may add dead helpers or a non-compiling harness; regression for Item A may never land
- **Proposed resolution**: Specify concrete edits: extend the inline sanitize-mermaid-fragment.sh stub (e.g. SANITIZE_REJECT=1 with SANITIZE_REASON_TOKEN env) and reuse assert_contains on captured stdout like the existing rejection case at lines 50-53

### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-generate-code-flow-diagram.sh:71-85
- **Concern**: Issue #2854 Item A cites loss of fence metadata on real sanitizer lines; plan regression only uses fictional REASON_TOKEN=pipe-in-node-label=foo. Scenario: Production-shaped lines from scripts/sanitize-mermaid-fragment.sh:201 (REASON_TOKEN=pipe-in-node-label fence=N line=M) could regress without failing CI
- **Proposed resolution**: Add a second assertion using the real sanitizer token shape (embedded spaces and fence=/line= suffixes), not only the hypothetical embedded-equals example

### FINDING_21:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-ci-failed-jobs.sh:87-93
- **Concern**: Third T8 acceptance (embedded newline must not create an extra logical log line) is not reachable with the fixed while IFS= read -r loop and no loop-structure changes. Scenario: gh stderr bytes split on newline before sanitize_diagnostic_line runs; the multiline-in-one-larch_err case from larch_err printf is not exercisable via the planned stub path
- **Proposed resolution**: Revise T8 to test control-byte stripping with a single read line (e.g. printf '%b' 'HTTP 500\x07Bad Gateway' without interior \n) and assert one captured stderr line; drop or re-scope the newline-count assertion unless the read loop changes

### FINDING_22:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:102-103
- **Concern**: Plan states no public output contract changes but Item A intentionally lengthens SKIP_REASON for live sanitizer rejections. Scenario: Downstream consumers that assumed token-only SKIP_REASON may see new fence=/line= suffixes; docs drift from behavior
- **Proposed resolution**: Note in generate-code-flow-diagram.md that SKIP_REASON now preserves the full REASON_TOKEN tail (including fence metadata) and that this is an intentional diagnostic enrichment

### FINDING_23:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/ci-failed-jobs.sh:125-128
- **Concern**: Plan audits only the stderr larch_err path but feature requires auditing other raw job-name emit sites. Scenario: A malformed gh job name with tabs or control bytes can still be written raw to TSV or direct emit output, splitting rows or confusing downstream consumers
- **Proposed resolution**: Sanitize or substitute a safe job-name value before every TSV/direct emit surface and add a regression with malformed job names containing tab/control bytes

### FINDING_24:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-failed-jobs.sh:79-81
- **Concern**: Planned stderr sanitization runs after read -r has already split on newline. Scenario: The stated newline hardening and T8 assertion cannot hold for crafted gh stderr containing newlines because extra larch_err records are created before sanitize_diagnostic_line runs
- **Proposed resolution**: Sanitize/fold the raw stderr stream before line splitting, or explicitly revise the contract to per-input-line control-byte stripping and drop the impossible embedded-newline assertion

### FINDING_25:
- **Reviewer(s)**: Cursor-dyn-harness-api-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-generate-code-flow-diagram.sh:13-16,50-53
- **Concern**: Plan test sketch calls write_sanitize_stub run_subject_skip_path $TROOT and assert_file_contains; none exist in this harness. Scenario: Implementer copies sketch verbatim and gets command-not-found or wrong assertion API; regression never lands
- **Proposed resolution**: Harness uses assert_contains(needle,haystack,label) TMP_ROOT/session dirs and one quoted-heredoc sanitizer stub at lines 35-39; rewrite sketch to match: e.g. extend stub to printf REASON_TOKEN from ${SANITIZE_REASON_TOKEN:-test-reject} at runtime run SANITIZE_REJECT=1 SANITIZE_REASON_TOKEN=pipe-in-node-label=foo assert_contains SKIP_REASON=pipe-in-node-label=foo on captured stdout variable

### FINDING_26:
- **Reviewer(s)**: Codex-dyn-harness-api-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-generate-code-flow-diagram.sh:13-53
- **Concern**: Plan sketch uses absent harness APIs write_sanitize_stub run_subject_skip_path and assert_file_contains; current harness only defines assert_contains and drives the subject inline. Scenario: Implementing the sketch verbatim fails with command not found, and assert_file_contains would be structurally wrong because out is captured stdout, not a file path
- **Proposed resolution**: Revise the plan to either add those helpers explicitly or adapt the new case to the existing harness: rewrite the sanitizer stub, run the existing cd repo invocation, and call assert_contains 'SKIP_REASON=pipe-in-node-label=foo' "$out" 'SKIP_REASON preserves value past second ='

### FINDING_27:
- **Reviewer(s)**: Codex-dyn-harness-api-fidelity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-ci-failed-jobs.sh:39-47; scripts/test-ci-failed-jobs.sh:67-72
- **Concern**: Plan offers extending GH_MODE=fail with GH_FAIL_STDERR_FILE, but run_subject currently exports only GH_MODE and GH_LINES_FILE into the subject environment. Scenario: A test can set GH_FAIL_STDERR_FILE in the shell, but the copied subject and child gh stub will not see it unless run_subject passes it through, so the injected stderr fixture path will be ignored
- **Proposed resolution**: Revise the plan to update run_subject with GH_FAIL_STDERR_FILE="${GH_FAIL_STDERR_FILE:-}" when choosing that fixture-file approach, or choose a fail-injected mode that does not depend on an unexported env var

### FINDING_28:
- **Reviewer(s)**: Codex-dyn-harness-api-fidelity
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/test-ci-failed-jobs.sh:16-24
- **Concern**: Plan calls for negative byte assertions and larch_err line-count assertions, but the harness assertion API only provides assert_file_contains and assert_rc. Scenario: An implementation that assumes assert_file_not_contains or an existing line-count assertion helper will fail or add inconsistent ad hoc checks
- **Proposed resolution**: Specify the exact assertion shape: add small helpers such as assert_file_not_contains_bytes and assert_line_count, or use the existing T6-style if grep pattern with ok/fail for each negative and count check

### OOS_1:
- **Description**: Per-call-site tr -d [:cntrl:] duplicates policy and leaves other larch_err passthrough sites unprotected. Scenario: Future scripts forwarding external stderr verbatim remain injectable unless each adds its own helper
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/lib-quiet.sh:97-103
- **Phase**: design

### OOS_2:
- **Description**: [OUT_OF_SCOPE] Another REASON_TOKEN parser still assumes tokens cannot contain equals. Scenario: If this PR makes embedded equals a supported REASON_TOKEN value across the Mermaid sanitizer contract, the warnings-log aggregation still truncates at the first equals/space
- **Reviewer**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/sanitize-mermaid-fragment.sh:283-285
- **Phase**: design

### OOS_3:
- **Description**: Issue #2798 suggested auditing any site that emits raw job names; plan audits only the line-80 larch_err path. Scenario: TSV rows and quiet emit at line 128 still carry raw job_name values from gh stdout (pre-existing); out of Step 1c stderr scope but not recorded as deferred
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/ci-failed-jobs.sh:125-128
- **Phase**: design
