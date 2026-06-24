# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 2 | 1 | 0 | accepted |
| FINDING_3 | 2 | 1 | 0 | accepted |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 2 | 1 | 0 | accepted |
| FINDING_6 | 0 | 3 | 0 | rejected |
| OOS_1 | 0 | 3 | 0 | rejected |
| OOS_2 | 0 | 3 | 0 | rejected |
| OOS_3 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| cursor-specialist-correctness | 4 | 3 | 0 | 1 | 2 | 0 | 0 | 2 | 2 | STATUS=OK |
| cursor-specialist-edge-cases | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 3 | STATUS=OK |
| cursor-specialist-testing | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | STATUS=OK |
| dyn-dyn-final-summary-contract | 1 | 0 | 0 | 1 | 2 | 0 | 0 | 2 | -3 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-final-summary-contract-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | cursor-plan-fidelity | 9 | 8 | 1 | 0 | 0.889 | false |
| code-review | cursor-pragmatism | 9 | 9 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 9 | 6 | 3 | 0 | 0.667 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | cursor-plan-fidelity | 3 | 0 | 2 | 1 | 0 | 0 | 0 | 0.667 | false |
| code-review | cursor-pragmatism | 4 | 1 | 3 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | cursor-validity | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1.000 | true |
