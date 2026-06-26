# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 3 | 0 | 0 | accepted |
| FINDING_2 | 3 | 0 | 0 | accepted |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 0 | 3 | 0 | rejected |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 3 | 0 | 0 | accepted |
| FINDING_9 | 1 | 2 | 0 | neutral |
| FINDING_10 | 1 | 2 | 0 | neutral |
| FINDING_11 | 0 | 3 | 0 | rejected |
| FINDING_12 | 0 | 3 | 0 | rejected |
| FINDING_13 | 2 | 1 | 0 | accepted |
| FINDING_14 | 0 | 3 | 0 | rejected |
| FINDING_15 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-edge-cases | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | STATUS=OK |
| codex-specialist-testing | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | STATUS=OK |
| cursor-specialist-correctness | 4 | 2 | 0 | 2 | 3 | 0 | 0 | 3 | -1 | STATUS=OK |
| cursor-specialist-edge-cases | 4 | 1 | 2 | 1 | 3 | 0 | 0 | 3 | -2.5 | STATUS=OK |
| cursor-specialist-testing | 2 | 0 | 0 | 2 | 3 | 0 | 0 | 3 | -5 | STATUS=OK |
| dyn-dyn-calibration-replay | 2 | 2 | 0 | 0 | 3 | 0 | 0 | 3 | 1 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 13 | 13 | 0 | 0 | 1.000 | false |
| code-review | codex-pragmatism | 13 | 12 | 1 | 0 | 0.923 | false |
| code-review | cursor-validity | 13 | 13 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 4 | 1 | 3 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | codex-pragmatism | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | cursor-validity | 4 | 0 | 4 | 0 | 0 | 0 | 0 | 1.000 | true |
