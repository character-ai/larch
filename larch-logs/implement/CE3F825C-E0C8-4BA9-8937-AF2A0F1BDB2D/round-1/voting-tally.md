# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 1 | 2 | 0 | neutral |
| FINDING_3 | 1 | 2 | 0 | neutral |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 3 | 0 | 0 | accepted |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 1 | 2 | 0 | neutral |
| FINDING_9 | 3 | 0 | 0 | accepted |
| FINDING_10 | 0 | 3 | 0 | rejected |
| FINDING_11 | 0 | 3 | 0 | rejected |
| FINDING_12 | 3 | 0 | 0 | accepted |
| FINDING_13 | 3 | 0 | 0 | accepted |
| FINDING_14 | 0 | 3 | 0 | rejected |
| FINDING_15 | 0 | 3 | 0 | rejected |
| FINDING_16 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | STATUS=OK |
| codex-specialist-edge-cases | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1.75 | STATUS=OK |
| codex-specialist-testing | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| cursor-specialist-correctness | 2 | 1 | 1 | 0 | 1 | 0 | 1 | 0 | 0.75 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 3 | 0 | 1 | 2 | -2 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 3 | -3 | STATUS=OK |
| dyn-dyn-gatec-persist | 3 | 3 | 0 | 0 | 1 | 0 | 0 | 1 | 4 | STATUS=OK |
| dyn-dyn-runlog-audit | 3 | 2 | 0 | 1 | 2 | 0 | 0 | 2 | 0 | STATUS=OK |
| dyn-dyn-gatec-persist-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-runlog-audit-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 13 | 13 | 0 | 0 | 1.000 | false |
| code-review | codex-pragmatism | 13 | 12 | 1 | 0 | 0.923 | false |
| code-review | cursor-validity | 13 | 13 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 5 | 0 | 3 | 2 | 0 | 0 | 0 | 0.600 | false |
| code-review | codex-pragmatism | 4 | 0 | 4 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | cursor-validity | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 1.000 | true |
