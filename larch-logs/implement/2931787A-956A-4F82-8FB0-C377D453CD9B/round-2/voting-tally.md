# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 1 | 2 | 0 | neutral |
| FINDING_2 | 0 | 3 | 0 | rejected |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 1 | 2 | 0 | neutral |
| FINDING_5 | 0 | 3 | 0 | rejected |
| FINDING_6 | 2 | 1 | 0 | accepted |
| FINDING_7 | 2 | 1 | 0 | accepted |
| FINDING_8 | 1 | 2 | 0 | neutral |
| FINDING_9 | 2 | 1 | 0 | accepted |
| FINDING_10 | 2 | 1 | 0 | accepted |
| FINDING_11 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1.75 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| cursor-specialist-correctness | 6 | 1 | 2 | 3 | 0 | 0 | 0 | 0 | -2.5 | STATUS=OK |
| cursor-specialist-edge-cases | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 3.75 | STATUS=OK |
| cursor-specialist-testing | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| dyn-dyn-dispatch-telemetry | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1.75 | STATUS=OK |
| dyn-dyn-skill-wires | 3 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-generalist | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 8 | 5 | 3 | 0 | 0.625 | false |
| code-review | codex-pragmatism | 8 | 8 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 8 | 7 | 1 | 0 | 0.875 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
| code-review | codex-pragmatism | 4 | 0 | 3 | 1 | 0 | 0 | 0 | 0.750 | 1.000 | false |
| code-review | cursor-validity | 3 | 0 | 2 | 1 | 0 | 0 | 0 | 0.667 | 1.000 | false |
