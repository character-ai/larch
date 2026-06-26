# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 1 | 2 | 0 | neutral |
| FINDING_2 | 0 | 3 | 0 | rejected |
| FINDING_3 | 1 | 2 | 0 | neutral |
| FINDING_4 | 1 | 2 | 0 | neutral |
| FINDING_5 | 0 | 3 | 0 | rejected |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 0 | 3 | 0 | rejected |
| FINDING_9 | 2 | 1 | 0 | accepted |
| FINDING_10 | 0 | 3 | 0 | rejected |
| FINDING_11 | 2 | 1 | 0 | accepted |
| FINDING_12 | 2 | 1 | 0 | accepted |
| FINDING_13 | 0 | 3 | 0 | rejected |
| FINDING_14 | 0 | 3 | 0 | rejected |
| FINDING_15 | 1 | 2 | 0 | neutral |
| FINDING_16 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | STATUS=OK |
| codex-specialist-edge-cases | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-testing | 3 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | -1.5 | STATUS=OK |
| cursor-specialist-correctness | 5 | 0 | 3 | 2 | 3 | 0 | 0 | 3 | -5.75 | STATUS=OK |
| cursor-specialist-edge-cases | 3 | 0 | 1 | 2 | 3 | 0 | 0 | 3 | -5.25 | STATUS=OK |
| cursor-specialist-testing | 3 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | -2.25 | STATUS=OK |
| dyn-dyn-calibration-replay | 3 | 0 | 2 | 1 | 3 | 0 | 0 | 3 | -4.5 | STATUS=OK |
| dyn-dyn-calibration-replay-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 12 | 12 | 0 | 0 | 1.000 | false |
| code-review | codex-pragmatism | 12 | 9 | 3 | 0 | 0.750 | false |
| code-review | cursor-validity | 12 | 12 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 3 | 0 | 2 | 1 | 0 | 0 | 0 | 0.667 | false |
| code-review | codex-pragmatism | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | false |
| code-review | cursor-validity | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 1.000 | true |
