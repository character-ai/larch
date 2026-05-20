# Review Round 3

- Mode: `diff`
- Accepted findings: 6
- Rejected findings: 3
- Exonerated findings: 2
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **[architecture]** [`skills/implement/SKILL.md:1682`](skills/implement/SKILL.md) — The sentence that describes `scripts/refresh-run-logs.sh` still says it “refreshes `larch:final-summary` only after `PR_URL` exists,” which remains true for that helper (`refresh-run-logs.sh` gates on `pr_url`). The same section was edited nearby for the new `ship-pr.sh` ordering, but this line still reads as the **whole** story for when `larch:final-summary` / `final-summary.md` first appear. Readers can infer incorrectly that nothing touches final-summary before `PR_URL` exists, even though `run_pr_create_phase` now runs a full `write-final-report.sh` **before** `create-pr.sh`. **Suggested fix:** Add a short clarifier in that sentence (or the preceding one), e.g. that `ship-pr.sh` seeds placeholder `final-summary.md` and an initial tracking upsert before PR creation, while `refresh-run-logs.sh`’s own `write-final-report.sh` call remains conditional on `PR_URL`.
- **Reviewer**: dyn-phase-ordering-output.txt
- **Concern**: - **[architecture]** [`skills/implement/SKILL.md:1682`](skills/implement/SKILL.md) — The sentence that describes `scripts/refresh-run-logs.sh` still says it “refreshes `larch:final-summary` only after `PR_URL` exists,” which remains true for that helper (`refresh-run-logs.sh` gates on `pr_url`). The same section was edited nearby for the new `ship-pr.sh` ordering, but this line still reads as the **whole** story for when `larch:final-summary` / `final-summary.md` first appear. Readers can infer incorrectly that nothing touches final-summary before `PR_URL` exists, even though `run_pr_create_phase` now runs a full `write-final-report.sh` **before** `create-pr.sh`. **Suggested fix:** Add a short clarifier in that sentence (or the preceding one), e.g. that `ship-pr.sh` seeds placeholder `final-summary.md` and an initial tracking upsert before PR creation, while `refresh-run-logs.sh`’s own `write-final-report.sh` call remains conditional on `PR_URL`.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: scripts/ship-pr.sh:956-963
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Pre-create write-final-report failure always uses exit_stall 9b without transient-net classification used for create-pr.sh. Transient GitHub/API outage on the first larch:final-summary upsert blocks PR creation entirely (no PR_URL yet), a stricter operational outcome than the pre-reorder flow where the PR already existed before a failing summary write could stall Step 9b. Mirror create-pr.sh: classify fail_file with is_transient_net_signature and exit_transient_net on match, or explicitly document and test this stricter mode.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: scripts/test-ship-pr.sh:260-302,618-660
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] write_state always pre-seeds PR_URL/PR_NUMBER and the write-final-report stub truncates its log each call. The pre-create empty-PR_URL placeholder path is never exercised; the PR_URL assertion can pass without proving the second-pass refresh behavior. Add a test variant with cleared PR fields or log both invocations without truncation.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/test-ship-pr.sh:260-303,618-660
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Pr-create ship-pr harness seeds PR_URL/PR_NUMBER and write-final-report stub truncates its log each call Production pre-create path expects empty PR fields and placeholder summary; tests never assert first full write or placeholder semantics; dropping pre-create write could still pass COMMENT_ONLY=true-only checks Use pr-create-specific state with empty PR fields; append-only stub logging; assert two invocations (no --comment-only then --comment-only) and/or PR N/A after first write
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: scripts/test-ship-pr.sh:618-860
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No test for LARCH_NO_LOGS_COMMIT=true skipping pre-PR larch-log commit Plan-listed edge case lacks automated regression guard Add a pr-create scenario with LARCH_NO_LOGS_COMMIT=true and assert larch-log commit is not invoked
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: skills/implement/SKILL.md:1680-1682
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Adjacent paragraphs mix ship-pr early final-summary behavior with refresh-run-logs gating without an explicit hand-off. A reader skimming Step 7a may think all larch:final-summary refreshes wait for PR_URL and miss that ship-pr writes before PR creation. Open the retry paragraph with an explicit subject such as In refresh-run-logs.sh so the two mechanisms are unambiguous.
- **Suggested revision**: Address the concern above.


