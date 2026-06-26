# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 2 | 1 | 0 | accepted |
| FINDING_3 | 3 | 0 | 0 | accepted |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 0 | 3 | 0 | rejected |
| FINDING_6 | 1 | 2 | 0 | neutral |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 1 | 2 | 0 | neutral |
| FINDING_9 | 2 | 1 | 0 | accepted |
| FINDING_10 | 2 | 1 | 0 | accepted |
| FINDING_11 | 3 | 0 | 0 | accepted |
| FINDING_12 | 3 | 0 | 0 | accepted |
| FINDING_13 | 3 | 0 | 0 | accepted |
| FINDING_14 | 3 | 0 | 0 | accepted |
| FINDING_15 | 1 | 2 | 0 | neutral |
| FINDING_16 | 2 | 1 | 0 | accepted |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-generalist | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-correctness | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | STATUS=OK |
| codex-specialist-edge-cases | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1.75 | STATUS=OK |
| codex-specialist-testing | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | STATUS=OK |
| cursor-specialist-correctness | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | STATUS=OK |
| cursor-specialist-edge-cases | 3 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | -2.25 | STATUS=OK |
| cursor-specialist-testing | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| dyn-dyn-retry-warnings | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| dyn-dyn-run-log-drops | 4 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 3.5 | STATUS=OK |
| dyn-dyn-threshold-accounting | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| dyn-dyn-threshold-accounting-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-retry-warnings-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-run-log-drops-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 13 | 11 | 2 | 0 | 0.846 | false |
| code-review | codex-pragmatism | 13 | 10 | 3 | 0 | 0.769 | false |
| code-review | cursor-validity | 13 | 13 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 8 | 1 | 4 | 3 | 0 | 0 | 0 | 0.625 | 1.000 | false |
| code-review | codex-pragmatism | 7 | 3 | 4 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
| code-review | cursor-validity | 10 | 1 | 9 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
