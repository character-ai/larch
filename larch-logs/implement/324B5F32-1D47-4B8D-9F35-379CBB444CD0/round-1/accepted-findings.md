### FINDING_1: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:1751-1918
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicate Test 52-54 labels after inserting new audit-scan tests CI logs and human grep for Test 52 hit two unrelated cases; maintenance and failure triage become ambiguous Renumber new or downstream tests so Test N labels are unique
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: scripts/verify-run-log-completeness.sh:99-115
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] manifest_steps_ran_empty does not treat absent/null steps_ran like jq .steps_ran // {} A bailed run with final-summary bail heading and no run-statistics can pass audit-scan but fail verify-run-log-completeness with MISSING=run-statistics.md when steps_ran is omitted or null. Normalize steps_ran like audit (missing/null to {}) before empty check; add a fixture without steps_ran key.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: skills/implement/SKILL.md:1579-1581
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Docs claim verify matches audit bail fallback for ambiguous empty steps_ran Operators may trust parity and misdiagnose CI vs audit-runs disagreements on manifests without steps_ran. Update SKILL text after aligning manifest_steps_ran_empty with audit jq semantics.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: test-audit-runs.sh:1751-1820; scripts/test-verify-run-log-completeness.sh:281-318
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No fixture for bailed-needs-user-input or absent steps_ran key Regex supports bailed-needs-user-input but regressions do not; absent-key parity bug is untested. Add two small fixtures per harness.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: skills/implement/scripts/write-final-report.sh:369-374
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Silent swallow on larch-log manifest update failure manifest can remain ambiguous despite SKILL invariant; only bail-signal fallback saves audits. Surface failure or tighten error handling per repo norms.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: skills/implement/scripts/write-final-report.sh:369-375
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Manifest update after bail uses larch-log.sh manifest with stderr discarded and || true. jq missing corrupt manifest or larch-log validation failure yields silent no-op leaving ambiguous {} and reliance on weaker audit heuristics. Propagate failures or emit_kv on non-zero exit remove unconditional swallow for this call.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: skills/implement/scripts/write-final-report.sh:369-375
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Manifest merge errors are swallowed (stderr discarded, exit ignored). larch-log manifest update fails or returns non-zero; steps_ran stays {} so audit still flags run-statistics for non-bailed outcomes with no fallback match. Remove silent discard; surface failure to stderr/run log or fail finalize; optional single retry.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: scripts/verify-run-log-completeness.sh:99-116
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] manifest_steps_ran_empty rejects missing steps_ran while audit treats it as {} via jq // {} Manifest without steps_ran key: audit bail fallback may skip step9a1 checks while verify still enforces them (or vice versa) on edge fixtures Align empty detection with jq semantics (missing/null => empty dict) and regression-test
- **Suggested revision**: Address the concern above.


### FINDING_25: **correctness** `skills/implement/scripts/write-final-report.sh:369-374` — The new `steps_ran.*=false` update is wrapped in `2>/dev/null || true`, so any failure from `larch-log.sh manifest` (missing `jq`, bad `--log-root`, “manifest not found”, permissions, etc.) is swallowed and the run can still ship with an ambiguous empty `steps_ran`, contradicting the adjacent SKILL text that says the manifest **MUST NOT** stay ambiguous and undermining the point of the implement-side fix. **Suggested fix:** drop the unconditional `|| true` (and preferably stderr suppression): let the script surface non-zero status, or on failure emit a visible `append-tool-failure` / `emit` breadcrumb and exit non-zero from `write-final-report` if honoring the invariant is load-bearing for the run log contract.
- **Reviewer**: dyn-manifest-bail-invariants-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/write-final-report.sh:369-374` — The new `steps_ran.*=false` update is wrapped in `2>/dev/null || true`, so any failure from `larch-log.sh manifest` (missing `jq`, bad `--log-root`, “manifest not found”, permissions, etc.) is swallowed and the run can still ship with an ambiguous empty `steps_ran`, contradicting the adjacent SKILL text that says the manifest **MUST NOT** stay ambiguous and undermining the point of the implement-side fix. **Suggested fix:** drop the unconditional `|| true` (and preferably stderr suppression): let the script surface non-zero status, or on failure emit a visible `append-tool-failure` / `emit` breadcrumb and exit non-zero from `write-final-report` if honoring the invariant is load-bearing for the run log contract.
- **Suggested revision**: Address the concern above.


### FINDING_26: **correctness** `.claude/skills/audit-runs/scripts/audit-scan-run.sh:146-157` and `scripts/verify-run-log-completeness.sh` (new `final_summary_heading_bail_signal`) — The defensive path only treats the first non-empty `final-summary.md` line as a bail signal when it ends with `bailed` or `bailed-needs-user-input`, while `write-final-report.sh:348-351` records the same manifest honesty for other terminal outcomes (`stalled`, `design-only`, `forked-dry-run`, `pr-created`, etc.). Historical directories with `steps_ran: {}` and a first line ending in `stalled` (or similar) therefore still infer step9a1 as reached and can keep false positives if the manifest update never ran or failed silently. The original problem statement also mentioned a `pr_number` null/absent heuristic, which this diff does not implement. **Suggested fix:** broaden the heading probe to the full set of non-merge terminal outcome suffixes you already persist in `final-summary.md`, and/or add the empty-`steps_ran` + missing-`pr_number` branch so legacy runs match the written dual-signal intent.
- **Reviewer**: dyn-manifest-bail-invariants-output.txt
- **Concern**: - **correctness** `.claude/skills/audit-runs/scripts/audit-scan-run.sh:146-157` and `scripts/verify-run-log-completeness.sh` (new `final_summary_heading_bail_signal`) — The defensive path only treats the first non-empty `final-summary.md` line as a bail signal when it ends with `bailed` or `bailed-needs-user-input`, while `write-final-report.sh:348-351` records the same manifest honesty for other terminal outcomes (`stalled`, `design-only`, `forked-dry-run`, `pr-created`, etc.). Historical directories with `steps_ran: {}` and a first line ending in `stalled` (or similar) therefore still infer step9a1 as reached and can keep false positives if the manifest update never ran or failed silently. The original problem statement also mentioned a `pr_number` null/absent heuristic, which this diff does not implement. **Suggested fix:** broaden the heading probe to the full set of non-merge terminal outcome suffixes you already persist in `final-summary.md`, and/or add the empty-`steps_ran` + missing-`pr_number` branch so legacy runs match the written dual-signal intent.
- **Suggested revision**: Address the concern above.


### FINDING_28: **correctness** `.claude/skills/audit-runs/scripts/audit-scan-run.sh:146-152` — `_rf_final_summary_bail_signal` feeds the first non-empty line from `awk 'NF { print; exit }'` straight into `grep -Eq 'bailed(-needs-user-input)?$'` without stripping a trailing carriage return, while `scripts/verify-run-log-completeness.sh:118-134` normalizes with `line.rstrip("\r\n")`. A CRLF-encoded `final-summary.md` can leave a `\r` before the newline so the line no longer ends with `bailed`, the bail probe fails in the audit path only, and `required-file-presence` can still fail for `run-statistics.md` on a bailed run that the verifier treats as OK (parity break and possible revival of the false-positive for that encoding). **Suggested fix:** Strip `\r` from `line` in `_rf_final_summary_bail_signal` (e.g. bash parameter expansion or `tr -d '\r'`) before `grep`, matching the Python helper’s behavior.
- **Reviewer**: dyn-audit-fallback-logic-output.txt
- **Concern**: - **correctness** `.claude/skills/audit-runs/scripts/audit-scan-run.sh:146-152` — `_rf_final_summary_bail_signal` feeds the first non-empty line from `awk 'NF { print; exit }'` straight into `grep -Eq 'bailed(-needs-user-input)?$'` without stripping a trailing carriage return, while `scripts/verify-run-log-completeness.sh:118-134` normalizes with `line.rstrip("\r\n")`. A CRLF-encoded `final-summary.md` can leave a `\r` before the newline so the line no longer ends with `bailed`, the bail probe fails in the audit path only, and `required-file-presence` can still fail for `run-statistics.md` on a bailed run that the verifier treats as OK (parity break and possible revival of the false-positive for that encoding). **Suggested fix:** Strip `\r` from `line` in `_rf_final_summary_bail_signal` (e.g. bash parameter expansion or `tr -d '\r'`) before `grep`, matching the Python helper’s behavior.
- **Suggested revision**: Address the concern above.


### FINDING_33: **risk-integration** `scripts/test-verify-run-log-completeness.sh:291-319` — Tests 17 and 19 (bail-signal + empty `steps_ran`, and explicit `step9a1=false` with a completed-style heading) follow the same harness pattern as earlier OK cases: they wrap the verifier in `|| true`, so the real exit status is discarded, and they only assert that the combined stdout/stderr string contains `OK`. That is weaker than asserting a zero exit code and that `MISSING=` never appears, so a future regression that printed a misleading `OK` fragment while still failing the check could slip through. **Suggested fix:** For positive-path cases, run the verifier without `|| true`, assert exit status 0, and add a negative check that the output does not contain `MISSING=` (or assert the output is exactly `OK` plus the expected trailing newline).
- **Reviewer**: dyn-test-fixture-coverage-output.txt
- **Concern**: - **risk-integration** `scripts/test-verify-run-log-completeness.sh:291-319` — Tests 17 and 19 (bail-signal + empty `steps_ran`, and explicit `step9a1=false` with a completed-style heading) follow the same harness pattern as earlier OK cases: they wrap the verifier in `|| true`, so the real exit status is discarded, and they only assert that the combined stdout/stderr string contains `OK`. That is weaker than asserting a zero exit code and that `MISSING=` never appears, so a future regression that printed a misleading `OK` fragment while still failing the check could slip through. **Suggested fix:** For positive-path cases, run the verifier without `|| true`, assert exit status 0, and add a negative check that the output does not contain `MISSING=` (or assert the output is exactly `OK` plus the expected trailing newline).
- **Suggested revision**: Address the concern above.


### FINDING_34: **risk-integration** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:1751-1763` — The new bail-signal fixture for Test 52 only covers a first line ending in plain `bailed`, while `_rf_final_summary_bail_signal` in `.claude/skills/audit-runs/scripts/audit-scan-run.sh:146-152` also treats `bailed-needs-user-input` as a bail suffix; the mirrored verifier test (`scripts/test-verify-run-log-completeness.sh:281-287`) has the same gap. A typo or partial mismatch in production templates for the longer suffix would not be caught by these regressions. **Suggested fix:** Add a sibling fixture (or extend Test 52 / Test 17) whose first non-empty `final-summary.md` line ends with `bailed-needs-user-input` and assert the same pass/OK expectation as the plain `bailed` case.
- **Reviewer**: dyn-test-fixture-coverage-output.txt
- **Concern**: - **risk-integration** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:1751-1763` — The new bail-signal fixture for Test 52 only covers a first line ending in plain `bailed`, while `_rf_final_summary_bail_signal` in `.claude/skills/audit-runs/scripts/audit-scan-run.sh:146-152` also treats `bailed-needs-user-input` as a bail suffix; the mirrored verifier test (`scripts/test-verify-run-log-completeness.sh:281-287`) has the same gap. A typo or partial mismatch in production templates for the longer suffix would not be caught by these regressions. **Suggested fix:** Add a sibling fixture (or extend Test 52 / Test 17) whose first non-empty `final-summary.md` line ends with `bailed-needs-user-input` and assert the same pass/OK expectation as the plain `bailed` case.
- **Suggested revision**: Address the concern above.


### FINDING_4: risk-integration: skills/implement/scripts/write-final-report.sh:369-374
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] larch-log manifest updates silenced with || true Manifest stays {} after a failed jq/write; audit false-positives persist with no operator-visible error Remove unconditional swallow; surface stderr or fail when manifest update cannot be applied
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: scripts/verify-run-log-completeness.sh:99-115
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] manifest_steps_ran_empty rejects missing/null steps_ran while audit-scan normalizes with jq .steps_ran // {} manifest has steps_ran null or omitted and bailed final-summary; audit skips step9a1 files but verify still reports MISSING run-statistics.md Treat missing/null steps_ran as empty dict like jq before len==0 check; refresh comment
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: skills/implement/scripts/write-final-report.sh:369-375
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Silent swallow of manifest merge failures larch-log manifest fails; steps_ran stays {}; bail regex mismatch restores false-positive Surface failure or structured warning; avoid unconditional 2>/dev/null || true for this path
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: scripts/verify-run-log-completeness.sh:80-82
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Stale comment about step9a1 suppression Maintainers may remove bail branch thinking it is dead Update comment to include bail-signal empty steps_ran behavior
- **Suggested revision**: Address the concern above.


