# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 1 | 2 | 0 | neutral |
| FINDING_3 | 1 | 2 | 0 | neutral |
| FINDING_4 | 1 | 2 | 0 | neutral |
| FINDING_5 | 1 | 1 | 1 | neutral |
| FINDING_6 | 0 | 2 | 1 | rejected |
| FINDING_7 | 0 | 2 | 1 | rejected |
| FINDING_8 | 1 | 1 | 1 | neutral |
| FINDING_9 | 0 | 2 | 1 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1.75 | STATUS=OK |
| codex-specialist-testing | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1.75 | STATUS=OK |
| cursor-specialist-correctness | 4 | 1 | 3 | 0 | 3 | 0 | 1 | 2 | -0.75 | STATUS=OK |
| cursor-specialist-edge-cases | 4 | 1 | 3 | 0 | 3 | 0 | 1 | 2 | -0.75 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 2 | 0 | 1 | 1 | -1 | STATUS=OK |
| dyn-dyn-auto-compose | 3 | 0 | 3 | 0 | 3 | 0 | 1 | 2 | -2.75 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-auto-compose-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 1 | 0 | 1 | 3 | 0.000 | false |
| code-review | codex-pragmatism | 4 | 4 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 4 | 4 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | false |
| code-review | codex-pragmatism | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | cursor-validity | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1.000 | true |
