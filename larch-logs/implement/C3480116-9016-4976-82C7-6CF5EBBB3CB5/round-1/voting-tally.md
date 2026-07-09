# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 0 | 3 | 0 | rejected |
| FINDING_2 | 3 | 0 | 0 | accepted |
| FINDING_3 | 3 | 0 | 0 | accepted |
| FINDING_4 | 2 | 1 | 0 | accepted |
| FINDING_5 | 2 | 1 | 0 | accepted |
| FINDING_6 | 1 | 2 | 0 | neutral |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 2 | 1 | 0 | accepted |
| FINDING_9 | 0 | 3 | 0 | rejected |
| FINDING_10 | 0 | 3 | 0 | rejected |
| FINDING_11 | 0 | 3 | 0 | rejected |
| FINDING_12 | 2 | 1 | 0 | accepted |
| FINDING_13 | 2 | 1 | 0 | accepted |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 2 | 2 | 0 | 0 | 1 | 0 | 1 | 0 | 4 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | -1 | STATUS=OK |
| codex-specialist-testing | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | STATUS=OK |
| cursor-specialist-correctness | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | -1 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 3 | 0 | 3 | 0 | 0 | STATUS=OK |
| cursor-specialist-plan-fidelity-auto | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | STATUS=OK |
| cursor-specialist-testing | 2 | 1 | 0 | 1 | 3 | 0 | 2 | 1 | -1 | STATUS=OK |
| dyn-dyn-scope-gate | 2 | 0 | 0 | 2 | 2 | 0 | 2 | 0 | -2 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-plan-fidelity-auto | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-scope-gate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-scope-gate-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 12 | 11 | 1 | 0 | 0.917 | false |
| code-review | codex-pragmatism | 12 | 8 | 4 | 0 | 0.667 | false |
| code-review | codex-validity | 12 | 12 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 6 | 2 | 4 | 0 | 0 | 0.333 | 1.000 | false |
| code-review | codex-pragmatism | 3 | 2 | 1 | 0 | 0 | 0.667 | 1.000 | false |
| code-review | codex-validity | 7 | 3 | 4 | 0 | 0 | 0.429 | 1.000 | false |
