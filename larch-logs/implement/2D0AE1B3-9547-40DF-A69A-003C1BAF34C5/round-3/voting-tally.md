# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 2 | 1 | 0 | accepted |
| FINDING_2 | 0 | 3 | 0 | rejected |
| FINDING_3 | 0 | 3 | 0 | rejected |
| FINDING_4 | 2 | 1 | 0 | accepted |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| cursor-specialist-correctness | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | -2 | STATUS=OK |
| cursor-specialist-testing | 3 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | -1 | STATUS=OK |
| dyn-dyn-retry-warnings | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-threshold-accounting | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-threshold-accounting-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-retry-warnings-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-run-log-drops-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 4 | 2 | 2 | 0 | 0.500 | false |
| code-review | codex-pragmatism | 4 | 4 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 4 | 4 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | false |
| code-review | codex-pragmatism | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
| code-review | cursor-validity | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0.000 | 1.000 | false |
