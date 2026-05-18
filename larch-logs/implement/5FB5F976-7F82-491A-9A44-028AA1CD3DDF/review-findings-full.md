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

### FINDING_1: panel [code-review/accepted]

## **Important** risk-integration — `larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/plan-review-tally.json:1`, `larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/code-review-tally.json:1`: the newly committed tally artifacts do not match the new contract in `docs/run-logs.md:55-75`. `plan-review-tally.json` and `code-review-tally.json` both omit `exonerated_count` and `neutral_count`; the code-review body also still reports rejected totals using old mixed semantics (`Rejected: 15` / `Rejected findings: 17`) while the embedded vote table includes exonerated outcomes. Concrete scenario: a run-log consumer validating this branch’s committed artifacts against the documented envelope fails required-field checks or aggregates exonerated findings as rejected. Regenerate or patch the committed run-log tally files so they include the new fields and strict rejected/exonerated/neutral counts.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** risk-integration — `larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/plan-review-tally.json:1`, `larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/code-review-tally.json:1`: the newly committed tally artifacts do not match the new contract in `docs/run-logs.md:55-75`. `plan-review-tally.json` and `code-review-tally.json` both omit `exonerated_count` and `neutral_count`; the code-review body also still reports rejected totals using old mixed semantics (`Rejected: 15` / `Rejected findings: 17`) while the embedded vote table includes exonerated outcomes. Concrete scenario: a run-log consumer validating this branch’s committed artifacts against the documented envelope fails required-field checks or aggregates exonerated findings as rejected. Regenerate or patch the committed run-log tally files so they include the new fields and strict rejected/exonerated/neutral counts.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## code-quality: scripts/test-write-tally.sh:63-76

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan-review JSON assertions omit exonerated_count and neutral_count Asymmetric coverage vs code-review assertions allows plan-only envelope regressions Add jq field asserts for exonerated_count and neutral_count on plan JSON like the code-review case
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## correctness: larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/plan-review-tally.json (committed example)

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Example plan-review-tally.json lacks exonerated_count/neutral_count keys while docs claim a shared envelope. Operators or schema checks comparing docs to committed example see a contract mismatch. Regenerate the example via updated compose-tally-record or adjust docs for optional fields on older artifacts.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## correctness: scripts/implement-finalize.sh:484-498

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] set -e after postbump larch-log commit persists into run_postbump which began with set +e Postbump tail may exit early or classify failures differently if a later command returns non-zero under errexit Restore prior errexit state or isolate commit in a subshell
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## correctness: scripts/redact-tmpdir-paths.sh:12-20 (diff hunks)

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Operator-repo path redaction uses [A-Za-z0-9_-]+ for the repo segment, missing many valid directory names. Concrete scenario: /Users/alice/work/my.repo/larch3/scripts/foo.sh stays unredacted (or partially unredacted), leaking operator-local paths into published GitHub text. Widen the repo-segment pattern to real path characters or narrow the documented guarantee to match the regex.
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## correctness: skills/review/scripts/review-core.sh:161-170,243-253,264-273,357-366

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan 1d pass-through of EXONERATED_COUNT/NEUTRAL_COUNT incomplete on early exits Callers or strict parsers reading review-core stdout on zero-findings, panel-failed, or main-agent-vote-required paths never receive EXONERATED_COUNT/NEUTRAL_COUNT keys; downstream jq/kv logic may treat missing as error or wrong default vs main path. Emit EXONERATED_COUNT=0 and NEUTRAL_COUNT=0 on every exit branch that already emits ACCEPTED_COUNT/REJECTED_COUNT.
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## risk-integration: scripts/test-write-tally.sh

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] write-tally harness never exercises non-zero --exonerated/--neutral through the real compose+write pipeline. Integration bugs in flag parsing or jq composition only show with non-zero counters. Add one code-review write case with non-zero exonerated/neutral and assert JSON output.
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## risk-integration: scripts/test-write-tally.sh:163-170

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Plan-review defaults test omits exonerated_count/neutral_count assertions JSON shape regression for plan tallies may go undetected Add jq field checks for the new envelope keys
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Nit** risk-integration — `scripts/larch-log-batches.md:33-42`: this batch contract still documents the old tally schema and example without `exonerated_count` / `neutral_count`, even though `scripts/compose-tally-record.sh:80-101` now emits them and `docs/run-logs.md:55-75` documents them. Update the example and schema prose so the canonical batch reference stays in sync.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** risk-integration — `scripts/larch-log-batches.md:33-42`: this batch contract still documents the old tally schema and example without `exonerated_count` / `neutral_count`, even though `scripts/compose-tally-record.sh:80-101` now emits them and `docs/run-logs.md:55-75` documents them. Update the example and schema prose so the canonical batch reference stays in sync.
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## risk-integration: skills/review/references/heavy-worker.md:63-79

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Heavy-worker review-summary JSON contract still documents only accepted/rejected totals without exonerated/neutral semantics while emit-tally now sources strict REJECTED_COUNT from tally summary keys. Subagent-written review-summary.json can disagree with Bash emit-tally output for the same round (e.g., neutral findings counted as rejected in JSON but not in tally), breaking any merge or audit that assumes one meaning. Update heavy-worker schema prose (and examples) to match tally/emit-tally semantics or bump schema_version and add explicit fields so both producers align.
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## security: scripts/redact-tmpdir-paths.sh:13-21 scripts/redact-tmpdir-paths.md:3-4

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Operator-repo path redaction is limited to /Users/.../ paths with a strict repo-dir character class while docs describe broader scrubbing of operator working-tree roots. Committed run logs or outbound publisher text from a Linux home directory or a repo path whose directory name falls outside [A-Za-z0-9_-] can still contain the operator’s absolute path after redaction. Extend sed coverage (e.g. /home/ mirror), relax repo segment matching to real clone names, or narrow the documented guarantee to match the regex.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## architecture: skills/review/scripts/emit-tally.sh:102-116

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] review-summary.json omits exonerated/neutral dimensions introduced for code-review-tally. Consumers of only review-summary.json cannot see exonerated/neutral totals without reading other artifacts. Extend JSON or document that those counts live elsewhere.
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## code-quality: larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/plan-review-tally.json:1 larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/code-review-tally.json:1

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Shipped tally JSON omits exonerated_count neutral_count and body headline predates new counters while docs and composer require the shared envelope Contract completeness audit against committed logs disagrees with updated run-logs.md and compose-tally-record in the same PR Re-flush run logs with current write-tally path or remove stale snapshot until it matches the documented envelope
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## **Important** (`correctness`) [larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/code-review-tally.json:1](larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/code-review-tally.json) and [larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/plan-review-tally.json:1](larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/plan-review-tally.json): The flushed tally JSON in this branch still uses the old envelope (no `exonerated_count` / `neutral_count`) while [docs/run-logs.md:26-37](docs/run-logs.md) and [scripts/larch-log-batches.md:51-54](scripts/larch-log-batches.md) now describe those keys as part of the shared tally shape. Concrete impact: anyone validating committed logs against the updated contract treats these files as non-conforming, or assumes the implementation never emits the new fields. Regenerate those JSON artifacts with the updated `write-tally.sh` / `compose-tally-record.sh` path (or adjust the docs if committed samples are intentionally grandfathered).

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **Important** (`correctness`) [larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/code-review-tally.json:1](larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/code-review-tally.json) and [larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/plan-review-tally.json:1](larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/plan-review-tally.json): The flushed tally JSON in this branch still uses the old envelope (no `exonerated_count` / `neutral_count`) while [docs/run-logs.md:26-37](docs/run-logs.md) and [scripts/larch-log-batches.md:51-54](scripts/larch-log-batches.md) now describe those keys as part of the shared tally shape. Concrete impact: anyone validating committed logs against the updated contract treats these files as non-conforming, or assumes the implementation never emits the new fields. Regenerate those JSON artifacts with the updated `write-tally.sh` / `compose-tally-record.sh` path (or adjust the docs if committed samples are intentionally grandfathered).
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## code-quality: scripts/implement-finalize.sh:481-484

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Duplicate set +e around larch-log write adds noise. Readability/maintainability only. Remove redundant set +e.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## code-quality: scripts/implement-finalize.sh:481-484 (diff hunk)

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Duplicate consecutive set +e after the new larch-log write without an intervening set -e. Minor readability noise in a hot path touched for logging. Remove the redundant set +e.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## correctness: larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/code-review-tally.json:1

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Top-level rejected_count (28) disagrees with embedded voting table where only two findings have Result rejected under new semantics. Auditor treats JSON rejected_count as strict rejected tally and finds contradiction with markdown vote breakdown. Regenerate tally JSON so counters derive from the same strict outcome set as the voting table / review-tally.env.
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## correctness: larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/plan-review-tally.json:1 larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/code-review-tally.json:1

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Committed tally JSON in the new run-log directory omits exonerated_count and neutral_count while docs and larch-log-batches.md define the shared envelope including those keys. Downstream validators or humans comparing committed logs to the updated contract see schema drift in the very PR that defines the new shape. Regenerate or rewrite the shipped larch-logs tally JSON using the updated write-tally/compose path so committed files include exonerated_count and neutral_count (including zeros for plan-review).
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## risk-integration: larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/code-review-tally.json:1 and larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/plan-review-tally.json:1

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Committed plan/code tally JSON on this branch omits exonerated_count/neutral_count required by updated batch/docs contract; code-review body still mixes legacy headline counts with newer per-finding tables. A validator jq 'has("exonerated_count")' fails on shipped logs; docs promise keys that are absent. Re-flush tallies with current write-tally/compose path or remove stale snapshot from PR.
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## risk-integration: larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/plan-review-tally.json (committed quick-mode JSON in diff)

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] plan-review tally JSON lacks exonerated_count/neutral_count while docs/batches contract lists them operators or strict validators see contradictory schema vs documented envelope regenerate log or ensure plan quick path always emits full envelope via write-tally/compose
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## risk-integration: skills/review/scripts/test-emit-tally.sh (~jq -e line after emit-tally run)

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] review-summary.json jq only checks accepted_count and rejected_count exonerated_count/neutral_count regressions in emit-tally JSON would not fail the harness extend jq -e to assert exonerated_count and neutral_count match the tally fixture
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## **Important** `risk-integration` `larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/plan-review-tally.json:1`, `larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/code-review-tally.json:1`: the committed run-log artifacts still use the old tally contract, while `docs/run-logs.md:55-75` now says both tally files include `exonerated_count` and `neutral_count`, and that rejected code-review findings list only strict `rejected` outcomes. Concrete scenario: a consumer validating shipped logs against the updated contract sees both tally JSON files missing the new fields; the code-review body also lists `### [exonerated]` entries under `## Rejected Code Review Findings`, so the branch still ships the exact stale rejected/exonerated shape this change is meant to eliminate. Regenerate or update these committed run-log batches after the final tally-contract changes, or explicitly document that historical committed run logs are exempt from the new schema.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/plan-review-tally.json:1`, `larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/code-review-tally.json:1`: the committed run-log artifacts still use the old tally contract, while `docs/run-logs.md:55-75` now says both tally files include `exonerated_count` and `neutral_count`, and that rejected code-review findings list only strict `rejected` outcomes. Concrete scenario: a consumer validating shipped logs against the updated contract sees both tally JSON files missing the new fields; the code-review body also lists `### [exonerated]` entries under `## Rejected Code Review Findings`, so the branch still ships the exact stale rejected/exonerated shape this change is meant to eliminate. Regenerate or update these committed run-log batches after the final tally-contract changes, or explicitly document that historical committed run logs are exempt from the new schema.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## **Nit** (`risk-integration`) [skills/review/scripts/test-emit-tally.sh:2735-2736](skills/review/scripts/test-emit-tally.sh): After extending `review-summary.json` with `exonerated_count` and `neutral_count`, the harness still only asserts `accepted_count` and `rejected_count` in the main `jq -e` check. Extend the assertion so regressions that drop the new keys fail CI.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 4. **Nit** (`risk-integration`) [skills/review/scripts/test-emit-tally.sh:2735-2736](skills/review/scripts/test-emit-tally.sh): After extending `review-summary.json` with `exonerated_count` and `neutral_count`, the harness still only asserts `accepted_count` and `rejected_count` in the main `jq -e` check. Extend the assertion so regressions that drop the new keys fail CI. ```tsv schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix 1	in_scope	important	correctness	larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/code-review-tally.json:1-1 Flushed code-review-tally.json omits exonerated_count and neutral_count while docs and larch-log-batches.md declare a shared envelope including those keys.	Contract readers or jq validators reject the committed sample or conclude the feature is incomplete.	Regenerate committed run-log JSON with the updated writer or document an explicit grandfathering rule for historical logs. 1	in_scope	important	correctness	larch-logs/implement/5FB5F976-7F82-491A-9A44-028AA1CD3DDF/plan-review-tally.json:1-1 Flushed plan-review-tally.json omits exonerated_count and neutral_count under the same updated contract.	Same mismatch risk for plan-review tallies in shipped logs.	Same as prior row for plan-review batch. 2	in_scope	latent	risk-integration	skills/review/scripts/emit-tally.sh:63-95 emit-tally uses grep with a $ anchor on _OUTCOME=rejected when building compact rejected listings.	CRLF-terminated review-tally.env yields no matches; rejected findings and JSON counts silently skew.	Strip carriage returns or avoid end-anchored grep on env files. 3	in_scope	important	risk-integration	scripts/redact-tmpdir-paths.sh:20-21 Operator-repo sed matches any two path segments under /Users or /home.	Paths such as /home/runner/work/ in CI logs are rewritten to OPERATOR_REPO_PATH, mislabeling non-operator roots in published text.	Tighten regex to real clone heuristics or document and accept CI false positives explicitly. 4	in_scope	nit	risk-integration	skills/review/scripts/test-emit-tally.sh:2735-2736 jq regression check ignores exonerated_count and neutral_count.	New fields can be dropped from review-summary.json without failing the harness.	Add jq assertions for the new counters. ```
- **Suggested revision**: Address the concern above.

