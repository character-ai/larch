# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 3 | 0 | 0 | accepted |
| FINDING_2 | 1 | 2 | 0 | neutral |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 0 | 3 | 0 | rejected |
| FINDING_6 | 2 | 1 | 0 | accepted |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 0 | 3 | 0 | rejected |
| FINDING_9 | 0 | 3 | 0 | rejected |
| FINDING_10 | 0 | 3 | 0 | rejected |
| FINDING_11 | 2 | 1 | 0 | accepted |
| FINDING_12 | 0 | 3 | 0 | rejected |
| FINDING_13 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-edge-cases | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | STATUS=OK |
| codex-specialist-testing | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| cursor-specialist-correctness | 4 | 1 | 1 | 2 | 1 | 0 | 0 | 1 | -1.25 | STATUS=OK |
| cursor-specialist-edge-cases | 3 | 1 | 1 | 1 | 3 | 0 | 0 | 3 | -2.25 | STATUS=OK |
| cursor-specialist-testing | 1 | 1 | 0 | 0 | 3 | 0 | 0 | 3 | -2 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 12 | 11 | 1 | 0 | 0.917 | false |
| code-review | codex-pragmatism | 12 | 12 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 12 | 11 | 1 | 0 | 0.917 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | codex-pragmatism | 3 | 0 | 2 | 1 | 0 | 0 | 0 | 0.667 | false |
| code-review | cursor-validity | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | true |
