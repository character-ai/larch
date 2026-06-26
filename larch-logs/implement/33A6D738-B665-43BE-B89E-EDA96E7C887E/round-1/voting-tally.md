# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 2 | 1 | 0 | accepted |
| FINDING_3 | 1 | 2 | 0 | neutral |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 0 | 3 | 0 | rejected |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-generalist | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-correctness | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | STATUS=OK |
| codex-specialist-edge-cases | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | STATUS=OK |
| codex-specialist-testing | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | STATUS=OK |
| cursor-specialist-correctness | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| cursor-specialist-edge-cases | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 1 | -1.25 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 3 | -3 | STATUS=OK |
| dyn-dyn-rebase-routing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-rebase-routing-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 6 | 6 | 0 | 0 | 1.000 | false |
| code-review | codex-pragmatism | 6 | 6 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 6 | 4 | 2 | 0 | 0.667 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | codex-pragmatism | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | cursor-validity | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | false |
