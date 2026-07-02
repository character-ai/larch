# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 1 | 2 | 0 | neutral |
| FINDING_2 | 0 | 3 | 0 | rejected |
| FINDING_3 | 2 | 1 | 0 | accepted |
| FINDING_4 | 1 | 2 | 0 | neutral |
| FINDING_5 | 2 | 1 | 0 | accepted |
| OOS_1 | 0 | 3 | 0 | rejected |
| OOS_2 | 0 | 3 | 0 | rejected |
| OOS_3 | 0 | 3 | 0 | rejected |
| OOS_4 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-generalist | 1 | 1 | 0 | 0 | 1 | 0 | 1 | 0 | 2 | STATUS=OK |
| codex-specialist-correctness | 1 | 1 | 0 | 0 | 1 | 0 | 1 | 0 | 2 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | STATUS=OK |
| cursor-specialist-correctness | 1 | 0 | 0 | 1 | 2 | 0 | 1 | 1 | -2 | STATUS=OK |
| cursor-specialist-edge-cases | 1 | 0 | 0 | 1 | 1 | 0 | 1 | 0 | -1 | STATUS=OK |
| cursor-specialist-testing | 1 | 0 | 0 | 1 | 1 | 0 | 1 | 0 | -1 | STATUS=OK |
| dyn-dyn-review-loop-routing | 1 | 1 | 0 | 0 | 4 | 0 | 1 | 3 | -1 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-generalist | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-review-loop-routing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-review-loop-routing-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 7 | 7 | 0 | 0 | 1.000 | false |
| code-review | codex-pragmatism | 7 | 5 | 2 | 0 | 0.714 | false |
| code-review | cursor-validity | 7 | 7 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
| code-review | codex-pragmatism | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | false |
| code-review | cursor-validity | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
