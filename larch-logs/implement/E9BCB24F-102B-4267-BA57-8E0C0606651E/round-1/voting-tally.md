# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 3 | 0 | 0 | accepted |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 0 | 3 | 0 | rejected |
| FINDING_6 | 1 | 2 | 0 | neutral |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-testing | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 3 | 1 | 0 | 2 | -1 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 3 | 1 | 1 | 1 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | cursor-plan-fidelity | 5 | 5 | 0 | 0 | 1.000 | false |
| code-review | cursor-pragmatism | 5 | 5 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 5 | 4 | 1 | 0 | 0.800 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | cursor-plan-fidelity | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0.500 | false |
| code-review | cursor-pragmatism | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0.500 | false |
| code-review | cursor-validity | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1.000 | true |
