# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 3 | 0 | 0 | accepted |
| FINDING_2 | 3 | 0 | 0 | accepted |
| FINDING_3 | 2 | 1 | 0 | accepted |
| FINDING_4 | 1 | 2 | 0 | neutral |
| FINDING_5 | 0 | 3 | 0 | rejected |
| FINDING_6 | 3 | 0 | 0 | accepted |
| FINDING_7 | 1 | 2 | 0 | neutral |
| FINDING_8 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-specialist-correctness | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-testing | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 3 | 0 | 2 | 1 | -1 | STATUS=OK |
| cursor-specialist-testing | 1 | 1 | 0 | 0 | 2 | 0 | 0 | 2 | -1 | STATUS=OK |
| cursor-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| codex-specialist-testing | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-tmpdir-lint-baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-tmpdir-lint-baseline-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 6 | 5 | 1 | 0 | 0.833 | false |
| code-review | codex-pragmatism | 6 | 6 | 0 | 0 | 1.000 | false |
| code-review | codex-validity | 6 | 6 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 3 | 1 | 2 | 0 | 0 | 0.333 | 1.000 | false |
| code-review | codex-pragmatism | 4 | 1 | 3 | 0 | 0 | 0.250 | 1.000 | false |
| code-review | codex-validity | 4 | 1 | 3 | 0 | 0 | 0.250 | 1.000 | false |
