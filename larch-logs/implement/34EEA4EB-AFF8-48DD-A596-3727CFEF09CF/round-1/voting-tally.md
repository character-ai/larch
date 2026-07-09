# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 2 | 1 | 0 | accepted |
| FINDING_3 | 2 | 1 | 0 | accepted |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 3 | 0 | 0 | accepted |
| FINDING_6 | 2 | 1 | 0 | accepted |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 3 | 0 | 0 | accepted |
| FINDING_9 | 2 | 1 | 0 | accepted |
| FINDING_10 | 3 | 0 | 0 | accepted |
| FINDING_11 | 0 | 3 | 0 | rejected |
| FINDING_12 | 1 | 2 | 0 | neutral |
| FINDING_13 | 2 | 1 | 0 | accepted |
| FINDING_14 | 2 | 1 | 0 | accepted |
| FINDING_15 | 0 | 3 | 0 | rejected |
| FINDING_16 | 0 | 3 | 0 | rejected |
| FINDING_17 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | STATUS=OK |
| codex-specialist-edge-cases | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | STATUS=OK |
| codex-specialist-testing | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | STATUS=OK |
| cursor-specialist-correctness | 4 | 4 | 0 | 0 | 2 | 0 | 0 | 2 | 3 | STATUS=OK |
| cursor-specialist-edge-cases | 5 | 4 | 0 | 1 | 1 | 0 | 0 | 1 | 3 | STATUS=OK |
| cursor-specialist-plan-fidelity-auto | 2 | 2 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | STATUS=OK |
| cursor-specialist-testing | 4 | 2 | 1 | 1 | 2 | 0 | 0 | 2 | -1.25 | STATUS=OK |
| dyn-dyn-statusline-security | 3 | 3 | 0 | 0 | 2 | 0 | 0 | 2 | 4 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-plan-fidelity-auto | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-statusline-security | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-statusline-security-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 16 | 16 | 0 | 0 | 1.000 | false |
| code-review | codex-pragmatism | 16 | 16 | 0 | 0 | 1.000 | false |
| code-review | codex-validity | 16 | 9 | 7 | 0 | 0.562 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 10 | 4 | 6 | 0 | 0 | 0.400 | 1.000 | false |
| code-review | codex-pragmatism | 10 | 6 | 4 | 0 | 0 | 0.600 | 1.000 | false |
| code-review | codex-validity | 3 | 3 | 0 | 0 | 0 | 1.000 | 0.000 | true |
