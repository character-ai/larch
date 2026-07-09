# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 1 | 2 | 0 | neutral |
| FINDING_2 | 3 | 0 | 0 | accepted |
| FINDING_3 | 2 | 1 | 0 | accepted |
| FINDING_4 | 1 | 2 | 0 | neutral |
| FINDING_5 | 2 | 1 | 0 | accepted |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 2 | 1 | 0 | accepted |
| FINDING_8 | 2 | 1 | 0 | accepted |
| FINDING_9 | 0 | 3 | 0 | rejected |
| FINDING_10 | 0 | 3 | 0 | rejected |
| FINDING_11 | 0 | 3 | 0 | rejected |
| FINDING_12 | 2 | 1 | 0 | accepted |
| FINDING_13 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 2 | 1 | 0 | 1 | 1 | 0 | 1 | 0 | 1 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | STATUS=OK |
| codex-specialist-testing | 1 | 0 | 0 | 1 | 3 | 1 | 2 | 0 | 0 | STATUS=OK |
| cursor-specialist-correctness | 2 | 2 | 0 | 0 | 2 | 0 | 2 | 0 | 4 | STATUS=OK |
| cursor-specialist-edge-cases | 2 | 1 | 0 | 1 | 5 | 1 | 3 | 1 | 1 | STATUS=OK |
| cursor-specialist-plan-fidelity-auto | 1 | 1 | 0 | 0 | 5 | 1 | 3 | 1 | 2 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 3 | 0 | 3 | 0 | 0 | STATUS=OK |
| dyn-dyn-scope-gate | 2 | 2 | 0 | 0 | 6 | 1 | 3 | 2 | 3 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-plan-fidelity-auto | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-scope-gate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 11 | 10 | 1 | 0 | 0.909 | false |
| code-review | codex-pragmatism | 11 | 8 | 3 | 0 | 0.727 | false |
| code-review | codex-validity | 11 | 10 | 1 | 0 | 0.909 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 5 | 3 | 2 | 0 | 0 | 0.600 | 1.000 | false |
| code-review | codex-pragmatism | 3 | 2 | 1 | 0 | 0 | 0.667 | 1.000 | false |
| code-review | codex-validity | 5 | 5 | 0 | 0 | 0 | 1.000 | 0.000 | true |
