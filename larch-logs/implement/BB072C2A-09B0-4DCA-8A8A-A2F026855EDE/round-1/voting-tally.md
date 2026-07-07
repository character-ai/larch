# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 3 | 0 | 0 | accepted |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 2 | 1 | 0 | accepted |
| FINDING_6 | 1 | 2 | 0 | neutral |
| FINDING_7 | 1 | 2 | 0 | neutral |
| FINDING_8 | 3 | 0 | 0 | accepted |
| FINDING_9 | 0 | 3 | 0 | rejected |
| FINDING_10 | 0 | 3 | 0 | rejected |
| FINDING_11 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0.75 | STATUS=OK |
| codex-specialist-edge-cases | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0.75 | STATUS=OK |
| codex-specialist-testing | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| cursor-specialist-correctness | 2 | 2 | 0 | 0 | 2 | 0 | 0 | 2 | 1 | STATUS=OK |
| cursor-specialist-edge-cases | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 1.75 | STATUS=OK |
| cursor-specialist-testing | 2 | 0 | 2 | 0 | 1 | 0 | 0 | 1 | -1.5 | STATUS=OK |
| dyn-dyn-bgjob-contract | 2 | 1 | 1 | 0 | 5 | 0 | 0 | 5 | -4.25 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-bgjob-contract | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-bgjob-contract-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 9 | 9 | 0 | 0 | 1.000 | false |
| code-review | codex-pragmatism | 9 | 8 | 1 | 0 | 0.889 | false |
| code-review | codex-validity | 9 | 8 | 1 | 0 | 0.889 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 4 | 3 | 1 | 0 | 0 | 0.750 | 1.000 | false |
| code-review | codex-pragmatism | 3 | 0 | 3 | 0 | 0 | 0.000 | 1.000 | false |
| code-review | codex-validity | 3 | 1 | 2 | 0 | 0 | 0.333 | 1.000 | false |
