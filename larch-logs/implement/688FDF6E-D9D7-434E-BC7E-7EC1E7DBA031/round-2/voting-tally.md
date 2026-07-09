# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 0 | 3 | 0 | rejected |
| FINDING_3 | 0 | 3 | 0 | rejected |
| OOS_1 | 2 | 0 | 1 | accepted |
| OOS_2 | 0 | 2 | 1 | rejected |
| OOS_3 | 0 | 2 | 1 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-edge-cases | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | STATUS=OK |
| codex-specialist-testing | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | STATUS=OK |
| cursor-specialist-correctness | 2 | 1 | 0 | 1 | 1 | 0 | 1 | 0 | 1 | STATUS=OK |
| cursor-specialist-edge-cases | 2 | 1 | 0 | 1 | 1 | 0 | 1 | 0 | 1 | STATUS=OK |
| cursor-specialist-plan-fidelity-auto | 1 | 1 | 0 | 0 | 1 | 0 | 1 | 0 | 2 | STATUS=OK |
| cursor-specialist-testing | 2 | 1 | 0 | 1 | 1 | 0 | 1 | 0 | 1 | STATUS=OK |
| dyn-dyn-scope-gate | 2 | 1 | 0 | 1 | 3 | 0 | 1 | 2 | -1 | STATUS=OK |
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
| code-review | codex-plan-fidelity | 3 | 3 | 0 | 3 | 1.000 | false |
| code-review | codex-pragmatism | 6 | 6 | 0 | 0 | 1.000 | false |
| code-review | codex-validity | 6 | 5 | 1 | 0 | 0.833 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 1 | 1 | 0 | 0 | 0 | 1.000 | 0.000 | true |
| code-review | codex-pragmatism | 2 | 1 | 1 | 0 | 0 | 0.500 | 1.000 | false |
| code-review | codex-validity | 1 | 0 | 1 | 0 | 0 | 0.000 | 1.000 | false |
