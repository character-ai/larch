# Code Review Voting Tally

## Per-finding vote breakdown

| Item | YES | NO | JERR | Result |
|---|---:|---:|---:|---|
| FINDING_1 | 3 | 0 | 0 | accepted |
| FINDING_2 | 0 | 3 | 0 | rejected |
| FINDING_3 | 3 | 0 | 0 | accepted |
| FINDING_4 | 3 | 0 | 0 | accepted |
| FINDING_5 | 3 | 0 | 0 | accepted |
| FINDING_6 | 1 | 2 | 0 | neutral |
| FINDING_7 | 1 | 2 | 0 | neutral |
| FINDING_8 | 0 | 3 | 0 | rejected |

## Reviewer Competition Scoreboard

| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| codex-generalist | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| codex-specialist-edge-cases | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | -1 | STATUS=OK |
| codex-specialist-testing | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 | STATUS=OK |
| cursor-specialist-correctness | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | STATUS=OK |
| cursor-specialist-testing | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | STATUS=OK |
| dyn-dyn-verdict-docs | 3 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0.75 | STATUS=OK |
| codex-specialist-correctness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| cursor-specialist-edge-cases | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-verdict-gates | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-verdict-gates-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-run-dir-joins | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-run-dir-joins-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |
| dyn-dyn-verdict-docs-codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=OK |

## Voter Agreement Scoreboard

| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |
|---|---|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 6 | 6 | 0 | 0 | 1.000 | false |
| code-review | codex-pragmatism | 6 | 6 | 0 | 0 | 1.000 | false |
| code-review | cursor-validity | 6 | 6 | 0 | 0 | 1.000 | false |

## Voter Severity Scoreboard

| Panel | Voter | YES Votes | Blocker | Major | Minor | Nit | Uncertain | Missing Severity | High Rate | Calibration Score | Uncalibrated |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| code-review | codex-plan-fidelity | 4 | 0 | 4 | 0 | 0 | 0 | 0 | 1.000 | 0.000 | true |
| code-review | codex-pragmatism | 4 | 0 | 1 | 3 | 0 | 0 | 0 | 0.250 | 1.000 | false |
| code-review | cursor-validity | 4 | 0 | 1 | 3 | 0 | 0 | 0 | 0.250 | 1.000 | false |
