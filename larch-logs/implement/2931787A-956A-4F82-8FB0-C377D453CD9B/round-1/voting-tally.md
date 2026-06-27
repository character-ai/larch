# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 2 | 1 | 0 | accepted |
| FINDING_3 | 3 | 0 | 0 | accepted |
| FINDING_4 | 3 | 0 | 0 | accepted |
| FINDING_5 | 3 | 0 | 0 | accepted |
| FINDING_6 | 3 | 0 | 0 | accepted |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 3 | 0 | 0 | accepted |
| FINDING_9 | 3 | 0 | 0 | accepted |
| FINDING_10 | 3 | 0 | 0 | accepted |
| FINDING_11 | 2 | 1 | 0 | accepted |
| FINDING_12 | 3 | 0 | 0 | accepted |
| FINDING_13 | 2 | 1 | 0 | accepted |
| FINDING_14 | 3 | 0 | 0 | accepted |
| FINDING_15 | 3 | 0 | 0 | accepted |
| OOS_1 | 0 | 3 | 0 | rejected |
| OOS_2 | 0 | 3 | 0 | rejected |
| OOS_3 | 0 | 3 | 0 | rejected |
| OOS_4 | 0 | 3 | 0 | rejected |
| OOS_5 | 0 | 3 | 0 | rejected |
| OOS_6 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-generalist | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-correctness | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | STATUS=OK |
| codex-specialist-edge-cases | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | STATUS=OK |
| codex-specialist-testing | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-correctness | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | STATUS=OK |
| cursor-specialist-edge-cases | 5 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 7 | STATUS=OK |
| cursor-specialist-testing | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | STATUS=OK |
| dyn-dyn-dispatch-telemetry | 3 | 3 | 0 | 0 | 1 | 0 | 0 | 1 | 4 | STATUS=OK |
| dyn-dyn-skill-wires | 5 | 5 | 0 | 0 | 2 | 0 | 0 | 2 | 8 | STATUS=OK |
| dyn-dyn-step4-composite | 3 | 2 | 0 | 1 | 4 | 0 | 0 | 4 | -1 | STATUS=OK |
| dyn-dyn-step4-composite-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-dispatch-telemetry-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-skill-wires-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 21 | 18 | 3 | 0 | 0.857 | false |
| code-review | codex-pragmatism | 21 | 20 | 1 | 0 | 0.952 | false |
| code-review | cursor-validity | 21 | 21 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 11 | 0 | 9 | 2 | 0 | 0 | 0 | 0.818 | 1.000 | false |
| code-review | codex-pragmatism | 13 | 0 | 9 | 4 | 0 | 0 | 0 | 0.692 | 1.000 | false |
| code-review | cursor-validity | 14 | 0 | 8 | 6 | 0 | 0 | 0 | 0.571 | 1.000 | false |
