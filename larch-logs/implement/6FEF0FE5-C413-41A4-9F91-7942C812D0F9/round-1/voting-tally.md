# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 3 | 0 | 0 | accepted |
| FINDING_2 | 1 | 2 | 0 | neutral |
| FINDING_3 | 3 | 0 | 0 | accepted |
| FINDING_4 | 1 | 2 | 0 | neutral |
| FINDING_5 | 1 | 1 | 1 | neutral |
| FINDING_6 | 2 | 1 | 0 | accepted |
| FINDING_7 | 0 | 2 | 1 | rejected |
| FINDING_8 | 3 | 0 | 0 | accepted |
| FINDING_9 | 0 | 2 | 1 | rejected |
| FINDING_10 | 0 | 2 | 1 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-testing | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| cursor-specialist-edge-cases | 1 | 1 | 0 | 0 | 1 | 0 | 1 | 0 | 2 | STATUS=OK |
| cursor-specialist-plan-fidelity-auto | 2 | 2 | 0 | 0 | 3 | 0 | 2 | 1 | 1 | STATUS=OK |
| cursor-specialist-testing | 2 | 1 | 1 | 0 | 1 | 0 | 1 | 0 | 0.75 | STATUS=OK |
| dyn-dyn-bgjob-handoff | 1 | 1 | 0 | 0 | 3 | 0 | 1 | 2 | -1 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-plan-fidelity-auto | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-bgjob-handoff | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-bgjob-handoff-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 7 | 7 | 0 | 0 | 1.000 | false |
| code-review | codex-pragmatism | 4 | 4 | 0 | 3 | 1.000 | false |
| code-review | codex-validity | 7 | 6 | 1 | 0 | 0.857 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 4 | 2 | 2 | 0 | 0 | 0.500 | 1.000 | false |
| code-review | codex-pragmatism | 4 | 1 | 3 | 0 | 0 | 0.250 | 1.000 | false |
| code-review | codex-validity | 3 | 2 | 1 | 0 | 0 | 0.667 | 1.000 | false |
