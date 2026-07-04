# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 1 | 2 | 0 | neutral |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 2 | 1 | 0 | accepted |
| FINDING_5 | 2 | 1 | 0 | accepted |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 1 | 2 | 0 | neutral |
| FINDING_8 | 2 | 1 | 0 | accepted |
| FINDING_9 | 0 | 3 | 0 | rejected |
| FINDING_10 | 1 | 2 | 0 | neutral |
| FINDING_11 | 2 | 1 | 0 | accepted |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-testing | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 2 | 0 | 1 | 1 | -1 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 3 | 1 | 1 | 1 | 0 | STATUS=OK |
| dyn-dyn-bgwait-marker | 0 | 0 | 0 | 0 | 2 | 1 | 1 | 0 | 1 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-bgwait-marker-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 8 | 3 | 5 | 0 | 0.375 | false |
| code-review | codex-pragmatism | 8 | 8 | 0 | 0 | 1.000 | false |
| code-review | codex-validity | 8 | 8 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | false |
| code-review | codex-pragmatism | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
| code-review | codex-validity | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
