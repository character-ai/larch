# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 3 | 0 | 0 | accepted |
| FINDING_3 | 1 | 2 | 0 | neutral |
| FINDING_4 | 3 | 0 | 0 | accepted |
| FINDING_5 | 0 | 3 | 0 | rejected |
| FINDING_6 | 3 | 0 | 0 | accepted |
| FINDING_7 | 1 | 2 | 0 | neutral |
| FINDING_8 | 1 | 2 | 0 | neutral |
| FINDING_9 | 1 | 2 | 0 | neutral |
| FINDING_10 | 1 | 2 | 0 | neutral |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-generalist | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-correctness | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-edge-cases | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | STATUS=OK |
| codex-specialist-testing | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| cursor-specialist-correctness | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 1.75 | STATUS=OK |
| cursor-specialist-edge-cases | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | -1 | STATUS=OK |
| cursor-specialist-testing | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0.75 | STATUS=OK |
| dyn-dyn-fn-joins | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| dyn-dyn-realized-outcomes | 5 | 1 | 3 | 1 | 0 | 0 | 0 | 0 | -0.75 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-generalist | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-fn-joins | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-fn-joins-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-realized-outcomes | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-realized-outcomes-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 5 | 4 | 1 | 0 | 0.800 | false |
| code-review | codex-pragmatism | 5 | 5 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 5 | 5 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 3 | 0 | 1 | 2 | 0 | 0 | 0 | 0.333 | 1.000 | false |
| code-review | codex-pragmatism | 4 | 0 | 3 | 1 | 0 | 0 | 0 | 0.750 | 1.000 | false |
| code-review | cursor-validity | 4 | 0 | 2 | 2 | 0 | 0 | 0 | 0.500 | 1.000 | false |
