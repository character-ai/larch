# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 3 | 0 | 0 | accepted |
| FINDING_2 | 1 | 2 | 0 | neutral |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 3 | 0 | 0 | accepted |
| FINDING_6 | 0 | 2 | 1 | rejected |
| FINDING_7 | 0 | 2 | 1 | rejected |
| FINDING_8 | 0 | 2 | 1 | rejected |
| FINDING_9 | 0 | 3 | 0 | rejected |
| FINDING_10 | 3 | 0 | 0 | accepted |
| FINDING_11 | 3 | 0 | 0 | accepted |
| FINDING_12 | 3 | 0 | 0 | accepted |
| FINDING_13 | 2 | 1 | 0 | accepted |
| FINDING_14 | 0 | 3 | 0 | rejected |
| FINDING_15 | 0 | 2 | 1 | rejected |
| FINDING_16 | 0 | 2 | 1 | rejected |
| FINDING_17 | 0 | 2 | 1 | rejected |
| FINDING_18 | 0 | 2 | 1 | rejected |
| FINDING_19 | 3 | 0 | 0 | accepted |
| FINDING_20 | 2 | 1 | 0 | accepted |
| FINDING_21 | 0 | 2 | 1 | rejected |
| FINDING_22 | 1 | 1 | 1 | neutral |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 4 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 5 | STATUS=OK |
| codex-specialist-edge-cases | 4 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 5 | STATUS=OK |
| codex-specialist-testing | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | STATUS=OK |
| cursor-specialist-correctness | 5 | 2 | 1 | 2 | 3 | 0 | 0 | 3 | -1.25 | STATUS=OK |
| cursor-specialist-edge-cases | 6 | 4 | 0 | 2 | 2 | 0 | 0 | 2 | 4 | STATUS=OK |
| cursor-specialist-testing | 2 | 1 | 0 | 1 | 3 | 0 | 0 | 3 | -2 | STATUS=OK |
| dyn-dyn-bgjob-lifecycle | 5 | 3 | 1 | 1 | 3 | 0 | 1 | 2 | 2.75 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-bgjob-lifecycle | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-bgjob-lifecycle-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 12 | 12 | 0 | 8 | 1.000 | false |
| code-review | codex-pragmatism | 20 | 20 | 0 | 0 | 1.000 | false |
| code-review | codex-validity | 20 | 18 | 2 | 0 | 0.900 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 8 | 8 | 0 | 0 | 0 | 1.000 | 0.000 | true |
| code-review | codex-pragmatism | 8 | 7 | 1 | 0 | 0 | 0.875 | 1.000 | false |
| code-review | codex-validity | 6 | 5 | 1 | 0 | 0 | 0.833 | 1.000 | false |
