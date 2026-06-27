# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 1 | 2 | 0 | neutral |
| FINDING_3 | 2 | 1 | 0 | accepted |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 2 | 1 | 0 | accepted |
| FINDING_6 | 1 | 2 | 0 | neutral |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 1 | 2 | 0 | neutral |
| FINDING_9 | 2 | 1 | 0 | accepted |
| FINDING_10 | 2 | 1 | 0 | accepted |
| FINDING_11 | 2 | 1 | 0 | accepted |
| FINDING_12 | 1 | 2 | 0 | neutral |
| FINDING_13 | 2 | 1 | 0 | accepted |
| OOS_1 | 0 | 3 | 0 | rejected |
| OOS_2 | 0 | 3 | 0 | rejected |
| OOS_3 | 0 | 3 | 0 | rejected |
| OOS_4 | 1 | 2 | 0 | neutral |
| OOS_5 | 0 | 3 | 0 | rejected |
| OOS_6 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-generalist | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| codex-specialist-correctness | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | -1 | STATUS=OK |
| codex-specialist-testing | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| cursor-specialist-correctness | 5 | 3 | 1 | 1 | 0 | 0 | 0 | 0 | 2.75 | STATUS=OK |
| cursor-specialist-edge-cases | 2 | 1 | 0 | 1 | 1 | 0 | 0 | 1 | 0 | STATUS=OK |
| cursor-specialist-testing | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | STATUS=OK |
| dyn-dyn-pause-gating | 3 | 2 | 1 | 0 | 1 | 0 | 1 | 0 | 1.75 | STATUS=OK |
| dyn-dyn-skill-contract | 5 | 2 | 2 | 1 | 3 | 0 | 0 | 3 | -1.5 | STATUS=OK |
| dyn-dyn-step2-routing | 3 | 1 | 0 | 2 | 2 | 0 | 0 | 2 | -2 | STATUS=OK |
| dyn-dyn-step2-routing-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-pause-gating-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-skill-contract-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 14 | 13 | 1 | 0 | 0.929 | false |
| code-review | codex-pragmatism | 14 | 8 | 6 | 0 | 0.571 | false |
| code-review | cursor-validity | 14 | 14 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 6 | 0 | 2 | 4 | 0 | 0 | 0 | 0.333 | 1.000 | false |
| code-review | codex-pragmatism | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0.000 | 1.000 | false |
| code-review | cursor-validity | 7 | 0 | 2 | 5 | 0 | 0 | 0 | 0.286 | 1.000 | false |
