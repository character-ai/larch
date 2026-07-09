# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 2 | 1 | 0 | accepted |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 3 | 0 | 0 | accepted |
| FINDING_5 | 1 | 2 | 0 | neutral |
| FINDING_6 | 1 | 2 | 0 | neutral |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 1 | 2 | 0 | neutral |
| FINDING_9 | 0 | 3 | 0 | rejected |
| FINDING_10 | 0 | 3 | 0 | rejected |
| FINDING_11 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 2 | 1 | 1 | 0 | 1 | STATUS=OK |
| codex-specialist-testing | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | -1.25 | STATUS=OK |
| cursor-specialist-correctness | 1 | 1 | 0 | 0 | 2 | 0 | 1 | 1 | 1 | STATUS=OK |
| cursor-specialist-edge-cases | 1 | 1 | 0 | 0 | 2 | 0 | 1 | 1 | 1 | STATUS=OK |
| cursor-specialist-plan-fidelity-auto | 0 | 0 | 0 | 0 | 4 | 0 | 3 | 1 | -1 | STATUS=OK |
| cursor-specialist-plan-fidelity-forced | 0 | 0 | 0 | 0 | 2 | 0 | 1 | 1 | -1 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 4 | 0 | 3 | 1 | -1 | STATUS=OK |
| dyn-dyn-bgjob-routing | 1 | 1 | 0 | 0 | 4 | 0 | 1 | 3 | -1 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-plan-fidelity-auto | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-plan-fidelity-forced | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-bgjob-routing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-bgjob-routing-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 8 | 8 | 0 | 0 | 1.000 | false |
| code-review | codex-pragmatism | 8 | 8 | 0 | 0 | 1.000 | false |
| code-review | codex-validity | 8 | 6 | 2 | 0 | 0.750 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 3 | 2 | 1 | 0 | 0 | 0.667 | 1.000 | false |
| code-review | codex-pragmatism | 3 | 2 | 1 | 0 | 0 | 0.667 | 1.000 | false |
| code-review | codex-validity | 1 | 1 | 0 | 0 | 0 | 1.000 | 0.000 | true |
