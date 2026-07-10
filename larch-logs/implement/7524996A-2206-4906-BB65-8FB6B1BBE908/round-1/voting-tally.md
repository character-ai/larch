# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 1 | 2 | 0 | neutral |
| FINDING_2 | 2 | 1 | 0 | accepted |
| FINDING_3 | 1 | 2 | 0 | neutral |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 2 | 1 | 0 | accepted |
| FINDING_6 | 1 | 2 | 0 | neutral |
| FINDING_7 | 2 | 1 | 0 | accepted |
| FINDING_8 | 3 | 0 | 0 | accepted |
| FINDING_9 | 0 | 3 | 0 | rejected |
| FINDING_10 | 2 | 1 | 0 | accepted |
| FINDING_11 | 0 | 3 | 0 | rejected |
| FINDING_12 | 0 | 3 | 0 | rejected |
| FINDING_13 | 0 | 3 | 0 | rejected |
| FINDING_14 | 0 | 3 | 0 | rejected |
| FINDING_15 | 1 | 2 | 0 | neutral |
| FINDING_16 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 2 | 2 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | STATUS=OK |
| codex-specialist-edge-cases | 3 | 2 | 1 | 0 | 1 | 0 | 0 | 1 | 0.75 | STATUS=OK |
| codex-specialist-testing | 1 | 1 | 0 | 0 | 1 | 0 | 1 | 0 | 2 | STATUS=OK |
| cursor-specialist-correctness | 2 | 1 | 1 | 0 | 6 | 0 | 2 | 4 | -3.25 | STATUS=OK |
| cursor-specialist-edge-cases | 2 | 0 | 1 | 1 | 5 | 0 | 2 | 3 | -4.25 | STATUS=OK |
| cursor-specialist-plan-fidelity-forced | 1 | 1 | 0 | 0 | 4 | 0 | 3 | 1 | 1 | STATUS=OK |
| cursor-specialist-testing | 1 | 1 | 0 | 0 | 2 | 0 | 2 | 0 | 2 | STATUS=OK |
| dyn-dyn-model-routing | 2 | 1 | 0 | 1 | 3 | 0 | 2 | 1 | -1 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-plan-fidelity-forced | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-model-routing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-model-routing-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 12 | 10 | 2 | 0 | 0.833 | false |
| code-review | codex-pragmatism | 12 | 10 | 2 | 0 | 0.833 | false |
| code-review | codex-validity | 12 | 12 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 3 | 0 | 3 | 0 | 0 | 0.000 | 1.000 | false |
| code-review | codex-pragmatism | 3 | 2 | 1 | 0 | 0 | 0.667 | 1.000 | false |
| code-review | codex-validity | 5 | 1 | 4 | 0 | 0 | 0.200 | 1.000 | false |
