# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | EXON | JERR | Result |
|---|---:|---:|---:|---:|---|
| FINDING_1 | 3 | 0 | 0 | 0 | accepted |
| FINDING_10 | 1 | 0 | 2 | 0 | exonerated |
| FINDING_11 | 0 | 1 | 2 | 0 | rejected |
| FINDING_12 | 3 | 0 | 0 | 0 | accepted |
| FINDING_13 | 3 | 0 | 0 | 0 | accepted |
| FINDING_14 | 3 | 0 | 0 | 0 | accepted |
| FINDING_15 | 1 | 0 | 2 | 0 | exonerated |
| FINDING_16 | 3 | 0 | 0 | 0 | accepted |
| FINDING_17 | 2 | 0 | 1 | 0 | accepted |
| FINDING_18 | 0 | 0 | 3 | 0 | rejected |
| FINDING_19 | 0 | 1 | 2 | 0 | rejected |
| FINDING_2 | 3 | 0 | 0 | 0 | accepted |
| FINDING_20 | 0 | 1 | 2 | 0 | rejected |
| FINDING_3 | 3 | 0 | 0 | 0 | accepted |
| FINDING_4 | 0 | 0 | 3 | 0 | rejected |
| FINDING_5 | 0 | 3 | 0 | 0 | rejected |
| FINDING_6 | 0 | 3 | 0 | 0 | rejected |
| FINDING_7 | 0 | 3 | 0 | 0 | rejected |
| FINDING_8 | 0 | 0 | 3 | 0 | rejected |
| FINDING_9 | 0 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral/Exon | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral/Exon | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Latent, `risk-integration`, [`skills/review/scripts/collect-findings.sh`](skills/review/scripts/collect-findings.sh) 281-284 — Any line matching `^##` starts a skip region until a canonical `### In-Scope Findings` or `### Out-of-Scope Observations` line. Reviewers who use non-canonical Markdown (for example `## In-Scope Findings` or other `##` section titles instead of the exact `###` headers) will have bullets and bodies under that region ignored, so real findings can be silently dropped while the raw file still reads as substantive. Scenario  A specialist template omits one `#` on the section header; Step 3a shows fewer findings than the reviewer intended with no hard failure. Suggested fix  Document the strict header grammar in the reviewer contract, add a narrow exception only if you must support `##` variants, or emit a warning when `skip` stayed 1 for the whole file but bullets existed after the first `##`. | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | STATUS=OK |
| codex-generalist | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | STATUS=OK |
| cursor-specialist-edge-cases | 2 | 1 | 0 | 1 | 2 | 0 | 0 | 2 | -2 | STATUS=OK |
| cursor-specialist-plan-fidelity | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-structure | 4 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | STATUS=OK |
| cursor-specialist-testing | 4 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-test-count-semantics | 1 | 1 | 0 | 0 | 4 | 0 | 0 | 4 | -3 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-security | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
