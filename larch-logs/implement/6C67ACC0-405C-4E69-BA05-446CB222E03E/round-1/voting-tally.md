# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 3 | 0 | 0 | accepted |
| FINDING_2 | 3 | 0 | 0 | accepted |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 3 | 0 | 0 | accepted |
| FINDING_5 | 2 | 1 | 0 | accepted |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 0 | 3 | 0 | rejected |
| FINDING_9 | 3 | 0 | 0 | accepted |
| FINDING_10 | 3 | 0 | 0 | accepted |
| FINDING_11 | 3 | 0 | 0 | accepted |
| FINDING_12 | 2 | 1 | 0 | accepted |
| FINDING_13 | 2 | 1 | 0 | accepted |
| FINDING_14 | 3 | 0 | 0 | accepted |
| FINDING_15 | 3 | 0 | 0 | accepted |
| FINDING_16 | 2 | 1 | 0 | accepted |
| FINDING_17 | 3 | 0 | 0 | accepted |
| FINDING_18 | 0 | 3 | 0 | rejected |
| FINDING_19 | 0 | 3 | 0 | rejected |
| FINDING_20 | 3 | 0 | 0 | accepted |
| FINDING_21 | 2 | 1 | 0 | accepted |
| FINDING_22 | 0 | 3 | 0 | rejected |
| FINDING_23 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | STATUS=OK |
| codex-specialist-edge-cases | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | STATUS=OK |
| codex-specialist-testing | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | STATUS=OK |
| cursor-specialist-correctness | 5 | 4 | 0 | 1 | 3 | 0 | 0 | 3 | 4 | STATUS=OK |
| cursor-specialist-edge-cases | 3 | 3 | 0 | 0 | 3 | 0 | 0 | 3 | 3 | STATUS=OK |
| cursor-specialist-testing | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | STATUS=OK |
| dyn-dyn-oos-verdicts | 3 | 3 | 0 | 0 | 2 | 0 | 0 | 2 | 4 | STATUS=OK |
| dyn-dyn-realized-matching | 5 | 5 | 0 | 0 | 3 | 0 | 0 | 3 | 7 | STATUS=OK |
| dyn-dyn-voter-prep | 3 | 2 | 0 | 1 | 3 | 0 | 0 | 3 | 0 | STATUS=OK |
| dyn-dyn-realized-matching-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-oos-verdicts-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-voter-prep-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | cursor-plan-fidelity | 23 | 23 | 0 | 0 | 1.000 | false |
| code-review | cursor-pragmatism | 23 | 23 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 23 | 18 | 5 | 0 | 0.783 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | cursor-plan-fidelity | 15 | 0 | 13 | 2 | 0 | 0 | 0 | 0.867 | false |
| code-review | cursor-pragmatism | 15 | 0 | 14 | 1 | 0 | 0 | 0 | 0.933 | true |
| code-review | cursor-validity | 10 | 0 | 10 | 0 | 0 | 0 | 0 | 1.000 | true |
