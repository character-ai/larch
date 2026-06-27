# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 0 | 3 | 0 | rejected |
| FINDING_2 | 1 | 2 | 0 | neutral |
| FINDING_3 | 1 | 2 | 0 | neutral |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 1 | 2 | 0 | neutral |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 0 | 3 | 0 | rejected |
| FINDING_9 | 1 | 2 | 0 | neutral |
| FINDING_10 | 2 | 1 | 0 | accepted |
| FINDING_11 | 0 | 3 | 0 | rejected |
| FINDING_12 | 0 | 3 | 0 | rejected |
| FINDING_13 | 0 | 3 | 0 | rejected |
| FINDING_14 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | -1.25 | STATUS=OK |
| codex-specialist-edge-cases | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | -0.5 | STATUS=OK |
| cursor-specialist-correctness | 3 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | -2.25 | STATUS=OK |
| cursor-specialist-edge-cases | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | -2 | STATUS=OK |
| cursor-specialist-testing | 3 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| dyn-dyn-closeout-oos | 4 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | -3.25 | STATUS=OK |
| dyn-dyn-step18-routing | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | -0.5 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-generalist | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-step18-routing-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-closeout-oos-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 10 | 9 | 1 | 0 | 0.900 | false |
| code-review | codex-pragmatism | 10 | 10 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 10 | 10 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | false |
| code-review | codex-pragmatism | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
| code-review | cursor-validity | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0.000 | 1.000 | false |
