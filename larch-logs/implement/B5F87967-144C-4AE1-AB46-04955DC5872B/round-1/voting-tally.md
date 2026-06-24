# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 0 | 3 | 0 | rejected |
| FINDING_2 | 3 | 0 | 0 | accepted |
| FINDING_3 | 2 | 1 | 0 | accepted |
| FINDING_4 | 0 | 2 | 1 | rejected |
| FINDING_5 | 0 | 2 | 1 | rejected |
| FINDING_6 | 0 | 2 | 1 | rejected |
| FINDING_7 | 0 | 2 | 1 | rejected |
| FINDING_8 | 0 | 2 | 1 | rejected |
| FINDING_9 | 0 | 2 | 1 | rejected |
| FINDING_10 | 0 | 2 | 1 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | STATUS=OK |
| codex-specialist-testing | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | -1 | STATUS=OK |
| cursor-specialist-correctness | 3 | 2 | 0 | 1 | 4 | 0 | 0 | 4 | -3 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 3 | -3 | STATUS=OK |
| cursor-specialist-testing | 2 | 1 | 0 | 1 | 3 | 0 | 0 | 3 | -3 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | cursor-plan-fidelity | 10 | 10 | 0 | 0 | 1.000 | false |
| code-review | cursor-pragmatism | 3 | 3 | 0 | 7 | 1.000 | false |
| code-review | cursor-validity | 10 | 9 | 1 | 0 | 0.900 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | cursor-plan-fidelity | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0.500 | false |
| code-review | cursor-pragmatism | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0.500 | false |
| code-review | cursor-validity | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0.000 | false |
