# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 3 | 0 | 0 | accepted |
| FINDING_2 | 2 | 1 | 0 | accepted |
| FINDING_3 | 0 | 3 | 0 | rejected |
| OOS_1 | 1 | 2 | 0 | neutral |
| OOS_2 | 0 | 3 | 0 | rejected |
| OOS_3 | 0 | 3 | 0 | rejected |
| OOS_4 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-testing | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| cursor-specialist-correctness | 2 | 2 | 0 | 0 | 1 | 0 | 1 | 0 | 4 | STATUS=OK |
| cursor-specialist-edge-cases | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| dyn-dyn-design-loads | 1 | 1 | 0 | 0 | 3 | 0 | 1 | 2 | 0 | STATUS=OK |
| dyn-dyn-implement-loads | 2 | 1 | 0 | 1 | 2 | 0 | 1 | 1 | 0 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-design-loads-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-implement-loads-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | cursor-plan-fidelity | 6 | 5 | 1 | 0 | 0.833 | false |
| code-review | cursor-pragmatism | 6 | 6 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 6 | 6 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | cursor-plan-fidelity | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0.000 | false |
| code-review | cursor-pragmatism | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | cursor-validity | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | true |
