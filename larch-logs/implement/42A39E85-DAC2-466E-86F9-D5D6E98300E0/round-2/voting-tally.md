# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 2 | 1 | 0 | accepted |
| FINDING_3 | 1 | 2 | 0 | neutral |
| OOS_1 | 0 | 3 | 0 | rejected |
| OOS_2 | 0 | 3 | 0 | rejected |
| OOS_3 | 0 | 3 | 0 | rejected |
| OOS_4 | 0 | 3 | 0 | rejected |
| OOS_5 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-testing | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| cursor-specialist-correctness | 1 | 1 | 0 | 0 | 2 | 0 | 0 | 2 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 1 | 1 | 0 | 0 | 3 | 0 | 0 | 3 | -1 | STATUS=OK |
| cursor-specialist-testing | 1 | 1 | 0 | 0 | 3 | 0 | 0 | 3 | -1 | STATUS=OK |
| dyn-dyn-guideline-parser | 2 | 2 | 0 | 0 | 3 | 0 | 0 | 3 | 1 | STATUS=OK |
| dyn-dyn-guideline-parser-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 7 | 6 | 1 | 0 | 0.857 | false |
| code-review | codex-pragmatism | 7 | 7 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 7 | 6 | 1 | 0 | 0.857 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | codex-pragmatism | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | cursor-validity | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1.000 | true |
