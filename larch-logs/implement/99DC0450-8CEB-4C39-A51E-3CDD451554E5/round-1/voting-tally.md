# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 1 | 2 | 0 | neutral |
| FINDING_2 | 3 | 0 | 0 | accepted |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 3 | 0 | 0 | accepted |
| FINDING_5 | 0 | 3 | 0 | rejected |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 3 | 0 | 0 | accepted |
| FINDING_8 | 2 | 1 | 0 | accepted |
| FINDING_9 | 0 | 3 | 0 | rejected |
| FINDING_10 | 0 | 3 | 0 | rejected |
| FINDING_11 | 0 | 3 | 0 | rejected |
| FINDING_12 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1.75 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| codex-specialist-testing | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| cursor-specialist-correctness | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 3 | -3 | STATUS=OK |
| cursor-specialist-testing | 2 | 1 | 1 | 0 | 3 | 0 | 0 | 3 | -1.25 | STATUS=OK |
| dyn-dyn-commit-route | 2 | 2 | 0 | 0 | 1 | 0 | 0 | 1 | 3 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-commit-route | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-commit-route-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | cursor-plan-fidelity | 11 | 11 | 0 | 0 | 1.000 | false |
| code-review | cursor-pragmatism | 11 | 11 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 11 | 10 | 1 | 0 | 0.909 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | cursor-plan-fidelity | 4 | 1 | 3 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | cursor-pragmatism | 4 | 1 | 3 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | cursor-validity | 3 | 1 | 1 | 1 | 0 | 0 | 0 | 0.667 | false |
