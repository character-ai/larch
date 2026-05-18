### FINDING_1: panel [code-review/accepted]

## **Important** correctness — `skills/implement/SKILL.md:1389-1393`, `skills/review-and-fix/scripts/review-and-fix.sh:728-801`: the new `exonerated_count` / `neutral_count` fields are not part of the final `/implement` Step 5 contract. `review-and-fix.sh` only passes the current round’s exonerated/neutral counts to `flush_review_batches`, while the skill’s final tally instructions still read only `accepted_count`, `rejected_count`, and `rounds_completed` and call `write-tally.sh` without `--exonerated` or `--neutral`. Concrete scenario: round 1 has one neutral finding and one accepted finding, the accepted fix triggers round 2, and round 2 has no neutral findings; the final `code-review-tally.json` reports `neutral_count: 0` even though the session had one neutral finding. Add exonerated/neutral totals to `review-and-fix-summary.json`, accumulate them like accepted/rejected, emit them from `review-and-fix.sh`, and update the Step 5 instructions to pass those totals into `write-tally.sh`.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** correctness — `skills/implement/SKILL.md:1389-1393`, `skills/review-and-fix/scripts/review-and-fix.sh:728-801`: the new `exonerated_count` / `neutral_count` fields are not part of the final `/implement` Step 5 contract. `review-and-fix.sh` only passes the current round’s exonerated/neutral counts to `flush_review_batches`, while the skill’s final tally instructions still read only `accepted_count`, `rejected_count`, and `rounds_completed` and call `write-tally.sh` without `--exonerated` or `--neutral`. Concrete scenario: round 1 has one neutral finding and one accepted finding, the accepted fix triggers round 2, and round 2 has no neutral findings; the final `code-review-tally.json` reports `neutral_count: 0` even though the session had one neutral finding. Add exonerated/neutral totals to `review-and-fix-summary.json`, accumulate them like accepted/rejected, emit them from `review-and-fix.sh`, and update the Step 5 instructions to pass those totals into `write-tally.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## correctness: scripts/implement-finalize.sh:464-492

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] postbump larch-log commit runs even when version-bump-reasoning write failed Commit can land without the reasoning batch the operator thinks failed write would block Commit only when write succeeded or skip commit on write failure
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## correctness: skills/review/scripts/tally-code-votes.sh:164-188

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Non-accepted in-scope branch lacks default case for unexpected classify_result. Unknown result drops file output while still emitting FINDING_*_ACCEPTED=false; silent tally/manifest skew vs prior behavior. Add *) fallback matching old append-to-rejected behavior or hard-fail with diagnostic.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** security — `scripts/redact-tmpdir-paths.sh:13-20`, `scripts/redact-tmpdir-paths.md:21-24`: the new `/Users/<name>/<repo>/` redaction misses JSON-escaped newline boundaries, unlike the existing tmpdir expressions. I verified `{"body":"first\\n/Users/alice/larch3/scripts/foo.sh"}` passes through unchanged, while a plain-line `/Users/alice/larch3/scripts/foo.sh` is redacted. This leaks operator-local repo paths in JSON log payloads where markdown bodies are embedded with `\n` escapes. Add a `(\n)`-style escaped-newline sed expression for `/Users/<name>/<repo>/` paths and cover it in `scripts/test-redact-tmpdir-paths.sh`.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** security — `scripts/redact-tmpdir-paths.sh:13-20`, `scripts/redact-tmpdir-paths.md:21-24`: the new `/Users/<name>/<repo>/` redaction misses JSON-escaped newline boundaries, unlike the existing tmpdir expressions. I verified `{"body":"first\\n/Users/alice/larch3/scripts/foo.sh"}` passes through unchanged, while a plain-line `/Users/alice/larch3/scripts/foo.sh` is redacted. This leaks operator-local repo paths in JSON log payloads where markdown bodies are embedded with `\n` escapes. Add a `(\n)`-style escaped-newline sed expression for `/Users/<name>/<repo>/` paths and cover it in `scripts/test-redact-tmpdir-paths.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## risk-integration: scripts/test-write-tally.sh:78-85

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No assertions on exonerated_count/neutral_count in written code-review-tally JSON. compose/write-tally JSON shape can regress without failing tests. Assert jq fields in test-write-tally.sh code-review paths.
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## risk-integration: skills/review-and-fix/scripts/review-and-fix.md:59-66 skills/review-and-fix/scripts/review-and-fix.sh:781-799

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Contract lists EXONERATED_COUNT and NEUTRAL_COUNT as stdout keys but review-and-fix.sh never emit_kv them Orchestrators parsing review-and-fix stdout never see those keys despite documentation Emit the keys or fix the contract to point at review-core.env
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## code-quality: scripts/redact-tmpdir-paths.sh:14-18

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] New OPERATOR_REPO_PATH sed not covered by scripts/test-redact-tmpdir-paths.sh. Regression in the new redaction rule ships without harness signal. Add cases to test-redact-tmpdir-paths.sh and extend redact-tmpdir-paths.md harness list per repo convention.
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## **Important** `risk-integration` `skills/review/scripts/tally-code-votes.sh:195`, affected: `skills/review/scripts/emit-tally.sh:50-57`, `skills/review-and-fix/scripts/review-and-fix.sh:430-498`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `skills/review/scripts/tally-code-votes.sh:195`, affected: `skills/review/scripts/emit-tally.sh:50-57`, `skills/review-and-fix/scripts/review-and-fix.sh:430-498`      Neutral and exonerated findings still flow through `review-tally.env` as `FINDING_N_ACCEPTED=false`, but `emit-tally.sh` treats every `ACCEPTED=false` as rejected. Concrete scenario: a 2-judge `YES/NO` split now correctly emits `REJECTED_COUNT=0` and `NEUTRAL_COUNT=1`, but `emit-tally.sh` writes `review-round-summary.md` and `review-summary.json` with `Rejected findings: 1`; `review-and-fix.sh` then embeds that stale summary into `code-review-tally.json.body`, reintroducing the counter mismatch this PR is meant to fix. Add an explicit outcome field/counter to `review-tally.env` and update `emit-tally.sh` plus its tests to count only `outcome=rejected` as rejected, or stop deriving rejected counts from the binary accepted flag.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## code-quality: skills/review/scripts/emit-tally.sh:50-98

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] emit-tally round summary and review-summary.json still count all FINDING_*_ACCEPTED=false lines as rejected while tally-code-votes now defines REJECTED_COUNT as strictly rejected-only When any in-scope finding is exonerated or neutral review-round-summary.md and review-summary.json report a larger rejected total than code-review-tally.json / tally stdout causing contradictory run audits Derive display and JSON counts from tally stdout keys or add explicit EXONERATED/NEUTRAL lines to review-tally.env and count them separately
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## correctness: skills/review/scripts/review-core.md (convergence note hunk in diff)

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Doc still steers callers to ACCEPTED_COUNT+REJECTED_COUNT only after REJECTED_COUNT semantics narrowed. Readers infer old semantics (non-accepted == rejected) and ignore EXONERATED_COUNT/NEUTRAL_COUNT. Mention the new counters in the convergence guidance.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## correctness: skills/review/scripts/tally-code-votes.sh:171-193

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Unknown classify_result falls through to rejected file and REJECTED_COUNT New or unexpected outcome strings misclassified as rejected with no hard failure Fail closed on unknown result or separate unknown counter without writing rejected-findings
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## risk-integration: scripts/ship-pr.sh run_pr_create_phase (RUN_ID guard per diff)

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Plan 1a implies always persisting pr_number after PR create; diff skips manifest/commit when read_state RUN_ID is empty. If RUN_ID is missing from state at pr-create, GitHub has a PR but manifest pr_number stays null; original gap can persist. Resolve run_id with fallbacks or explicit policy so manifest update is not RUN_ID-gated when logs are active.
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## risk-integration: scripts/ship-pr.sh:666-683

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] larch-log commit runs after manifest even when manifest failed Manifest update can fail while a subsequent commit still lands; manifest can remain without pr_number despite PR existing Gate commit on manifest rc==0 or use atomic update+commit helper
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## risk-integration: scripts/test-implement-finalize.sh:1122-1134 vs scripts/implement-finalize.sh:484-496

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Only negative coverage for postbump larch-log commit. Success-path commit could be deleted or never run when LOG_WRITE_STATUS=ok; CI still passes. Extend test-implement-finalize.sh: after a normal successful postbump, grep the stub argv log for a commit invocation following write with expected args.
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## risk-integration: scripts/test-ship-pr.sh vs scripts/ship-pr.sh:662-683

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No harness coverage for new pr-create manifest+commit tail. A refactor drops the block or breaks larch-log argv order; manifest stays without pr_number until postmerge and the regression ships green. Add a pr-create happy-path case in test-ship-pr.sh that stubs create-pr success, sets RUN_ID, and asserts stub log contains manifest pr_number= and commit with matching run-id.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## code-quality: docs/run-logs.md:55-74

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Documentation describes plan-review and code-review tally envelopes inconsistently with compose-tally-record which emits exonerated_count and neutral_count for every phase Plan-review docs omit keys that appear in committed JSON and code-review text claims additive fields relative to plan-review though both envelopes share the same shape Update plan-review and code-review subsections to list the shared JSON envelope or change the composer to omit zero fields on plan-review
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## code-quality: scripts/implement-finalize.md:57

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Output contract prose order of breadcrumbs vs larch-log commit does not match write_version_reasoning_fragment Misleading for operators tracing stdout order Align contract text with actual ordering in write_version_reasoning_fragment
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1258-1260

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] code-review-tally body header omits exonerated/neutral while JSON includes those fields. Human skim of body vs JSON suggests inconsistent tallies. Add exonerated/neutral to the summary line or document the split.
- **Suggested revision**: Address the concern above.

