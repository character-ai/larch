# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 1 | 2 | 0 | neutral |
| FINDING_2 | 1 | 2 | 0 | neutral |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 1 | 2 | 0 | neutral |
| FINDING_5 | 0 | 3 | 0 | rejected |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 2 | 1 | 0 | accepted |
| FINDING_8 | 0 | 3 | 0 | rejected |
| FINDING_9 | 0 | 3 | 0 | rejected |
| FINDING_10 | 0 | 3 | 0 | rejected |
| FINDING_11 | 1 | 2 | 0 | neutral |
| FINDING_12 | 3 | 0 | 0 | accepted |
| FINDING_13 | 1 | 2 | 0 | neutral |
| FINDING_14 | 0 | 3 | 0 | rejected |
| FINDING_15 | 0 | 3 | 0 | rejected |
| FINDING_16 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 1 | 0 | 0 | 1 | 1 | 0 | 1 | 0 | -1 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-testing | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| cursor-specialist-correctness | 1 | 0 | 0 | 1 | 2 | 0 | 2 | 0 | -1 | STATUS=OK |
| cursor-specialist-edge-cases | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | -1 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 3 | -3 | STATUS=OK |
| dyn-dyn-marker-safety | 1 | 1 | 0 | 0 | 4 | 0 | 1 | 3 | -1 | STATUS=OK |
| codex-generalist | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-guideline-drift | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-guideline-drift-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-marker-safety-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 11 | 11 | 0 | 0 | 1.000 | false |
| code-review | codex-pragmatism | 11 | 10 | 1 | 0 | 0.909 | false |
| code-review | cursor-validity | 11 | 11 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | codex-pragmatism | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1.000 | true |
| code-review | cursor-validity | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | true |
