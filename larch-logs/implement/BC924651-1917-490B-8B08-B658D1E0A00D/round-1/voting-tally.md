# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 3 | 0 | 0 | accepted |
| FINDING_2 | 2 | 1 | 0 | accepted |
| FINDING_3 | 3 | 0 | 0 | accepted |
| FINDING_4 | 2 | 1 | 0 | accepted |
| FINDING_5 | 2 | 1 | 0 | accepted |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 2 | 1 | 0 | accepted |
| FINDING_9 | 3 | 0 | 0 | accepted |
| FINDING_10 | 1 | 2 | 0 | neutral |
| FINDING_11 | 1 | 2 | 0 | neutral |
| FINDING_12 | 1 | 2 | 0 | neutral |
| OOS_1 | 0 | 3 | 0 | rejected |
| OOS_2 | 3 | 0 | 0 | accepted |
| OOS_3 | 0 | 3 | 0 | rejected |
| OOS_4 | 1 | 2 | 0 | neutral |
| OOS_5 | 3 | 0 | 0 | accepted |
| OOS_6 | 3 | 0 | 0 | accepted |
| OOS_7 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 3 | STATUS=OK |
| codex-specialist-edge-cases | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | STATUS=OK |
| codex-specialist-testing | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-correctness | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | STATUS=OK |
| cursor-specialist-edge-cases | 2 | 1 | 0 | 1 | 2 | 0 | 1 | 1 | -1 | STATUS=OK |
| cursor-specialist-testing | 4 | 2 | 2 | 0 | 4 | 0 | 3 | 1 | 0.5 | STATUS=OK |
| dyn-dyn-recovery-state | 3 | 0 | 1 | 2 | 2 | 0 | 1 | 1 | -3.25 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-recovery-state | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-recovery-state-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 15 | 13 | 2 | 0 | 0.867 | false |
| code-review | codex-pragmatism | 15 | 14 | 1 | 0 | 0.933 | false |
| code-review | codex-validity | 15 | 14 | 1 | 0 | 0.933 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 8 | 2 | 6 | 0 | 0 | 0.250 | 1.000 | false |
| code-review | codex-pragmatism | 9 | 2 | 7 | 0 | 0 | 0.222 | 1.000 | false |
| code-review | codex-validity | 9 | 4 | 5 | 0 | 0 | 0.444 | 1.000 | false |
