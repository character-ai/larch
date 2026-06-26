# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 0 | 3 | 0 | rejected |
| FINDING_2 | 3 | 0 | 0 | accepted |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 1 | 2 | 0 | neutral |
| FINDING_6 | 1 | 2 | 0 | neutral |
| FINDING_7 | 3 | 0 | 0 | accepted |
| FINDING_8 | 0 | 3 | 0 | rejected |
| FINDING_9 | 0 | 3 | 0 | rejected |
| FINDING_10 | 1 | 2 | 0 | neutral |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-generalist | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| codex-specialist-correctness | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1.75 | STATUS=OK |
| codex-specialist-edge-cases | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1.75 | STATUS=OK |
| codex-specialist-testing | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| cursor-specialist-correctness | 4 | 1 | 0 | 3 | 0 | 0 | 0 | 0 | -1 | STATUS=OK |
| cursor-specialist-edge-cases | 3 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 1.5 | STATUS=OK |
| cursor-specialist-testing | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | -2 | STATUS=OK |
| dyn-dyn-cursor-degraded-calibration | 4 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 3.5 | STATUS=OK |
| dyn-dyn-cursor-degraded-calibration-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 7 | 7 | 0 | 0 | 1.000 | false |
| code-review | codex-pragmatism | 7 | 7 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 7 | 7 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
| code-review | codex-pragmatism | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
| code-review | cursor-validity | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
