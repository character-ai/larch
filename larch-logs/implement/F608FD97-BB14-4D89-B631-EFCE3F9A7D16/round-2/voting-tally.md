# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 3 | 0 | 0 | accepted |
| FINDING_2 | 2 | 1 | 0 | accepted |
| FINDING_3 | 1 | 2 | 0 | neutral |
| FINDING_4 | 1 | 2 | 0 | neutral |
| FINDING_5 | 1 | 2 | 0 | neutral |
| FINDING_6 | 0 | 3 | 0 | rejected |
| FINDING_7 | 0 | 3 | 0 | rejected |
| FINDING_8 | 1 | 2 | 0 | neutral |
| FINDING_9 | 0 | 3 | 0 | rejected |
| FINDING_10 | 0 | 3 | 0 | rejected |
| FINDING_11 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | STATUS=OK |
| codex-specialist-testing | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | STATUS=OK |
| cursor-specialist-correctness | 4 | 2 | 2 | 0 | 3 | 0 | 1 | 2 | 0.5 | STATUS=OK |
| cursor-specialist-edge-cases | 2 | 1 | 1 | 0 | 3 | 0 | 1 | 2 | -1.25 | STATUS=OK |
| dyn-dyn-load-closure | 3 | 2 | 1 | 0 | 3 | 0 | 0 | 3 | -0.25 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-load-closure | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 7 | 7 | 0 | 0 | 1.000 | false |
| code-review | codex-pragmatism | 7 | 7 | 0 | 0 | 1.000 | false |
| code-review | codex-validity | 7 | 6 | 1 | 0 | 0.857 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 2 | 1 | 1 | 0 | 0 | 0.500 | 1.000 | false |
| code-review | codex-pragmatism | 2 | 2 | 0 | 0 | 0 | 1.000 | 0.000 | true |
| code-review | codex-validity | 1 | 0 | 1 | 0 | 0 | 0.000 | 1.000 | false |
