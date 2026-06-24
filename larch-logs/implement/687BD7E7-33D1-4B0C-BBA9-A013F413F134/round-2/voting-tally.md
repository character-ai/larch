# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 1 | 2 | 0 | neutral |
| FINDING_2 | 2 | 1 | 0 | accepted |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 0 | 3 | 0 | rejected |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-generic | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| cursor-specialist-correctness | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 3 | -3 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 3 | -3 | STATUS=OK |
| dyn-dyn-design-wait-contracts | 2 | 1 | 0 | 1 | 3 | 0 | 0 | 3 | -3 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | cursor-plan-fidelity | 6 | 6 | 0 | 0 | 1.000 | false |
| code-review | cursor-pragmatism | 6 | 5 | 1 | 0 | 0.833 | false |
| code-review | cursor-validity | 6 | 6 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | cursor-plan-fidelity | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0.000 | false |
| code-review | cursor-pragmatism | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | false |
| code-review | cursor-validity | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1.000 | true |
