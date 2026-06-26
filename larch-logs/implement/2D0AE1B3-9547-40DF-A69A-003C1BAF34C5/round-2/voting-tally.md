# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 0 | 3 | 0 | rejected |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 3 | 0 | 0 | accepted |
| FINDING_5 | 0 | 3 | 0 | rejected |
| FINDING_6 | 1 | 2 | 0 | neutral |
| FINDING_7 | 3 | 0 | 0 | accepted |
| FINDING_8 | 0 | 3 | 0 | rejected |
| FINDING_9 | 1 | 2 | 0 | neutral |
| FINDING_10 | 0 | 3 | 0 | rejected |
| FINDING_11 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-generalist | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-correctness | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | -1 | STATUS=OK |
| codex-specialist-edge-cases | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | -1.25 | STATUS=OK |
| codex-specialist-testing | 3 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | -2.25 | STATUS=OK |
| cursor-specialist-correctness | 5 | 2 | 0 | 3 | 0 | 0 | 0 | 0 | 1 | STATUS=OK |
| cursor-specialist-testing | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 3 | STATUS=OK |
| dyn-dyn-retry-warnings | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 3 | STATUS=OK |
| dyn-dyn-run-log-drops | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | -3 | STATUS=OK |
| dyn-dyn-threshold-accounting | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 3 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 9 | 8 | 1 | 0 | 0.889 | false |
| code-review | codex-pragmatism | 9 | 9 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 9 | 9 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
| code-review | codex-pragmatism | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
| code-review | cursor-validity | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
