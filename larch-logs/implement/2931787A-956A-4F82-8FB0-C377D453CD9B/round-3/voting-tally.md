# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 2 | 1 | 0 | accepted |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 1 | 2 | 0 | neutral |
| FINDING_5 | 0 | 3 | 0 | rejected |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 1 | 2 | 0 | neutral |
| FINDING_9 | 0 | 3 | 0 | rejected |
| FINDING_10 | 0 | 3 | 0 | rejected |
| FINDING_11 | 2 | 1 | 0 | accepted |
| FINDING_12 | 1 | 2 | 0 | neutral |
| FINDING_13 | 1 | 2 | 0 | neutral |
| FINDING_14 | 1 | 2 | 0 | neutral |
| FINDING_15 | 0 | 3 | 0 | rejected |
| FINDING_16 | 2 | 1 | 0 | accepted |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 3 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| codex-specialist-edge-cases | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0.75 | STATUS=OK |
| codex-specialist-testing | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 2.75 | STATUS=OK |
| cursor-specialist-correctness | 7 | 2 | 1 | 4 | 0 | 0 | 0 | 0 | -1.25 | STATUS=OK |
| cursor-specialist-edge-cases | 6 | 3 | 1 | 2 | 0 | 0 | 0 | 0 | 2.75 | STATUS=OK |
| cursor-specialist-testing | 4 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 2.5 | STATUS=OK |
| dyn-dyn-dispatch-telemetry | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| dyn-dyn-skill-wires | 6 | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 2.5 | STATUS=OK |
| dyn-dyn-step4-composite | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | STATUS=OK |
| dyn-dyn-step4-composite-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-dispatch-telemetry-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-skill-wires-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 11 | 9 | 2 | 0 | 0.818 | false |
| code-review | codex-pragmatism | 11 | 9 | 2 | 0 | 0.818 | false |
| code-review | cursor-validity | 11 | 11 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0.500 | 1.000 | false |
| code-review | codex-pragmatism | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0.500 | 1.000 | false |
| code-review | cursor-validity | 4 | 0 | 4 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
