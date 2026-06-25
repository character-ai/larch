# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 1 | 1 | 1 | neutral |
| FINDING_2 | 1 | 1 | 1 | neutral |
| FINDING_3 | 0 | 2 | 1 | rejected |
| FINDING_4 | 1 | 1 | 1 | neutral |
| FINDING_5 | 0 | 2 | 1 | rejected |
| FINDING_6 | 0 | 2 | 1 | rejected |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 2 | 1 | 0 | accepted |
| FINDING_9 | 0 | 3 | 0 | rejected |
| FINDING_10 | 1 | 2 | 0 | neutral |
| FINDING_11 | 0 | 2 | 1 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-testing | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | -1 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 3 | 0 | 2 | 1 | -1 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 3 | 0 | 1 | 2 | -2 | STATUS=OK |
| dyn-dyn-static-coverage | 3 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | -0.25 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-review-topology | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-review-topology-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-static-coverage-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 3 | 3 | 0 | 4 | 1.000 | false |
| code-review | codex-pragmatism | 7 | 7 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 7 | 6 | 1 | 0 | 0.857 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | codex-pragmatism | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | cursor-validity | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | false |
