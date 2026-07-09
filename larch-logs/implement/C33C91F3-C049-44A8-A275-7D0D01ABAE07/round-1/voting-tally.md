# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 0 | 3 | 0 | rejected |
| FINDING_2 | 2 | 1 | 0 | accepted |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 0 | 3 | 0 | rejected |
| FINDING_6 | 2 | 1 | 0 | accepted |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 1 | 2 | 0 | neutral |
| FINDING_9 | 1 | 2 | 0 | neutral |
| FINDING_10 | 0 | 3 | 0 | rejected |
| FINDING_11 | 0 | 3 | 0 | rejected |
| FINDING_12 | 0 | 3 | 0 | rejected |
| FINDING_13 | 3 | 0 | 0 | accepted |
| FINDING_14 | 2 | 1 | 0 | accepted |
| FINDING_15 | 1 | 2 | 0 | neutral |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | -1 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | -1 | STATUS=OK |
| codex-specialist-testing | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 3 | 0 | 1 | 2 | -2 | STATUS=OK |
| cursor-specialist-edge-cases | 2 | 0 | 0 | 2 | 1 | 0 | 0 | 1 | -3 | STATUS=OK |
| cursor-specialist-testing | 3 | 1 | 2 | 0 | 3 | 0 | 0 | 3 | -2.5 | STATUS=OK |
| dyn-dyn-static-resolver | 2 | 2 | 0 | 0 | 4 | 0 | 2 | 2 | 1 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-plan-fidelity-auto | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-static-resolver | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-static-resolver-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 12 | 12 | 0 | 0 | 1.000 | false |
| code-review | codex-pragmatism | 12 | 11 | 1 | 0 | 0.917 | false |
| code-review | codex-validity | 12 | 10 | 2 | 0 | 0.833 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 4 | 1 | 3 | 0 | 0 | 0.250 | 1.000 | false |
| code-review | codex-pragmatism | 3 | 1 | 2 | 0 | 0 | 0.333 | 1.000 | false |
| code-review | codex-validity | 2 | 1 | 1 | 0 | 0 | 0.500 | 1.000 | false |
