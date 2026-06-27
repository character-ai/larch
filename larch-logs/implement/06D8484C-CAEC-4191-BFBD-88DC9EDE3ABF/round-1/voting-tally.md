# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 1 | 2 | 0 | neutral |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 0 | 3 | 0 | rejected |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 1 | 2 | 0 | neutral |
| FINDING_8 | 1 | 2 | 0 | neutral |
| FINDING_9 | 2 | 1 | 0 | accepted |
| FINDING_10 | 1 | 2 | 0 | neutral |
| FINDING_11 | 3 | 0 | 0 | accepted |
| FINDING_12 | 1 | 2 | 0 | neutral |
| FINDING_13 | 0 | 3 | 0 | rejected |
| FINDING_14 | 1 | 2 | 0 | neutral |
| FINDING_15 | 0 | 3 | 0 | rejected |
| FINDING_16 | 2 | 1 | 0 | accepted |
| FINDING_17 | 0 | 3 | 0 | rejected |
| FINDING_18 | 0 | 3 | 0 | rejected |
| FINDING_19 | 1 | 2 | 0 | neutral |
| FINDING_20 | 2 | 1 | 0 | accepted |
| FINDING_21 | 1 | 2 | 0 | neutral |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-generalist | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | -1 | STATUS=OK |
| codex-specialist-correctness | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | -1 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 2 | 1 | 1 | 0 | 1 | STATUS=OK |
| cursor-specialist-correctness | 2 | 0 | 0 | 2 | 2 | 1 | 1 | 0 | -1 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 2 | 0 | 1 | 1 | -1 | STATUS=OK |
| cursor-specialist-testing | 1 | 1 | 0 | 0 | 1 | 0 | 1 | 0 | 1 | STATUS=OK |
| dyn-dyn-gantt-labels | 1 | 1 | 0 | 0 | 2 | 0 | 2 | 0 | 2 | STATUS=OK |
| dyn-dyn-round-window | 1 | 0 | 0 | 1 | 2 | 1 | 0 | 1 | -1 | STATUS=OK |
| dyn-dyn-timing-ledger | 1 | 0 | 0 | 1 | 1 | 0 | 1 | 0 | -1 | STATUS=OK |
| dyn-dyn-timing-ledger-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-round-window-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-gantt-labels-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 13 | 10 | 3 | 0 | 0.769 | false |
| code-review | codex-pragmatism | 13 | 12 | 1 | 0 | 0.923 | false |
| code-review | cursor-validity | 13 | 13 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0.500 | 1.000 | false |
| code-review | codex-pragmatism | 4 | 0 | 2 | 2 | 0 | 0 | 0 | 0.500 | 1.000 | false |
| code-review | cursor-validity | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
