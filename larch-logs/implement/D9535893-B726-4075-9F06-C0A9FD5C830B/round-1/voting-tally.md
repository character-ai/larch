# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 3 | 0 | 0 | accepted |
| FINDING_2 | 2 | 1 | 0 | accepted |
| FINDING_3 | 1 | 2 | 0 | neutral |
| FINDING_4 | 0 | 3 | 0 | rejected |
| FINDING_5 | 1 | 2 | 0 | neutral |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 1 | 2 | 0 | neutral |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | STATUS=OK |
| cursor-specialist-correctness | 2 | 2 | 0 | 0 | 1 | 0 | 1 | 0 | 3 | STATUS=OK |
| cursor-specialist-edge-cases | 2 | 2 | 0 | 0 | 2 | 0 | 1 | 1 | 2 | STATUS=OK |
| cursor-specialist-testing | 2 | 2 | 0 | 0 | 2 | 0 | 1 | 1 | 2 | STATUS=OK |
| dyn-dyn-bgjob-kv | 5 | 2 | 1 | 2 | 3 | 0 | 2 | 1 | -0.25 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-bgjob-kv | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-bgjob-kv-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 5 | 4 | 1 | 0 | 0.800 | false |
| code-review | codex-pragmatism | 5 | 5 | 0 | 0 | 1.000 | false |
| code-review | codex-validity | 5 | 5 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 1 | 1 | 0 | 0 | 0 | 1.000 | 0.000 | true |
| code-review | codex-pragmatism | 2 | 2 | 0 | 0 | 0 | 1.000 | 0.000 | true |
| code-review | codex-validity | 2 | 0 | 2 | 0 | 0 | 0.000 | 1.000 | false |
