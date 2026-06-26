# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 1 | 2 | 0 | neutral |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 1 | 2 | 0 | neutral |
| FINDING_5 | 1 | 2 | 0 | neutral |
| FINDING_6 | 1 | 2 | 0 | neutral |
| FINDING_7 | 1 | 2 | 0 | neutral |
| FINDING_8 | 0 | 3 | 0 | rejected |
| FINDING_9 | 0 | 3 | 0 | rejected |
| FINDING_10 | 0 | 3 | 0 | rejected |
| FINDING_11 | 2 | 1 | 0 | accepted |
| FINDING_12 | 0 | 3 | 0 | rejected |
| FINDING_13 | 0 | 3 | 0 | rejected |
| FINDING_14 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | -0.5 | STATUS=OK |
| codex-specialist-edge-cases | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | -1.25 | STATUS=OK |
| codex-specialist-testing | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | -2 | STATUS=OK |
| cursor-specialist-correctness | 2 | 1 | 0 | 1 | 1 | 0 | 1 | 0 | 1 | STATUS=OK |
| cursor-specialist-edge-cases | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | -0.75 | STATUS=OK |
| cursor-specialist-testing | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | -1 | STATUS=OK |
| dyn-dyn-auto-compose | 3 | 1 | 1 | 1 | 2 | 0 | 0 | 2 | -1.25 | STATUS=OK |
| dyn-dyn-auto-compose-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 9 | 9 | 0 | 0 | 1.000 | false |
| code-review | codex-pragmatism | 9 | 8 | 1 | 0 | 0.889 | false |
| code-review | cursor-validity | 9 | 8 | 1 | 0 | 0.889 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | codex-pragmatism | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | cursor-validity | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1.000 | true |
