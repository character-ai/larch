# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 3 | 0 | 0 | accepted |
| FINDING_2 | 1 | 2 | 0 | neutral |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 2 | 1 | 0 | accepted |
| FINDING_5 | 3 | 0 | 0 | accepted |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 1 | 2 | 0 | neutral |
| FINDING_8 | 3 | 0 | 0 | accepted |
| FINDING_9 | 1 | 2 | 0 | neutral |
| FINDING_10 | 1 | 2 | 0 | neutral |
| FINDING_11 | 1 | 2 | 0 | neutral |
| FINDING_12 | 1 | 2 | 0 | neutral |
| FINDING_13 | 0 | 3 | 0 | rejected |
| FINDING_14 | 1 | 2 | 0 | neutral |
| FINDING_15 | 1 | 2 | 0 | neutral |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-testing | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| cursor-specialist-correctness | 3 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1.75 | STATUS=OK |
| cursor-specialist-edge-cases | 2 | 1 | 0 | 1 | 1 | 1 | 0 | 0 | 2 | STATUS=OK |
| cursor-specialist-testing | 4 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | -1 | STATUS=OK |
| dyn-dyn-codex-role-routing | 4 | 1 | 2 | 1 | 2 | 0 | 2 | 0 | 0.5 | STATUS=OK |
| dyn-dyn-codex-role-routing-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | cursor-plan-fidelity | 7 | 7 | 0 | 0 | 1.000 | false |
| code-review | cursor-pragmatism | 7 | 7 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 7 | 6 | 1 | 0 | 0.857 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | cursor-plan-fidelity | 4 | 1 | 2 | 0 | 1 | 0 | 0 | 0.750 | false |
| code-review | cursor-pragmatism | 4 | 1 | 2 | 1 | 0 | 0 | 0 | 0.750 | false |
| code-review | cursor-validity | 3 | 1 | 2 | 0 | 0 | 0 | 0 | 1.000 | true |
