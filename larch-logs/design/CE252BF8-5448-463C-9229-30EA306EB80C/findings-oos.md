### OOS_1: [OUT_OF_SCOPE] Parallel CI log pointer outside report/git sweep
- **Description**: [OUT_OF_SCOPE] Parallel CI log pointer outside report/git sweep. Scenario: `collect_failed_logs()` emits the same `--- CI log … — last …` pattern as `gh.py`, but it lives under `python/larch/implement/`, outside the issue’s report/git directory bound.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/implement/ci_monitor.py:1009-1012
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Timing-ledger step labels still carry em dashes
- **Description**: [OUT_OF_SCOPE] Timing-ledger step labels still carry em dashes. Scenario: Even after changing the generic `{label} — started` separator, echoed `step_label` values come from timing marks written outside `python/larch/report/` (e.g. `Step 5 — code review`), so live progress text can still contain em dashes without further non-report edits.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/report/_progress_report_live.py:322-324
- **Phase**: design



### OOS_3: Redact truncation sentinel still contains an em dash and can surface in PR bodies and summaries composed by report/git modules
- **Description**: Redact truncation sentinel still contains an em dash and can surface in PR bodies and summaries composed by report/git modules. Scenario: Issue sweep targets report/ and git/ sources only; truncation text from core/redact.py can still appear in user-visible composed output when PEM redaction triggers
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/core/redact.py:29-30
- **Phase**: design



### OOS_4: [OUT_OF_SCOPE] Duplicate CI log pointer with the same em-dash pattern lives outside `report/` and `git/`
- **Description**: [OUT_OF_SCOPE] Duplicate CI log pointer with the same em-dash pattern lives outside `report/` and `git/`. Scenario: CI-fix output can still show an em dash even after this issue’s directory sweep passes
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/implement/ci_monitor.py:1010
- **Phase**: design



### OOS_5: [OUT_OF_SCOPE] PEM truncation marker injected through `pr_body.redact_pr_body` still contains an em dash
- **Description**: [OUT_OF_SCOPE] PEM truncation marker injected through `pr_body.redact_pr_body` still contains an em dash. Scenario: Rare PR-body redaction failures can still emit `—` in user-visible PR text although the source file is outside the planned sweep
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: security
- **Location**: python/larch/core/redact.py:30
- **Phase**: design



### OOS_6: [OUT_OF_SCOPE] `execution-issues.md` warning strings under `implement/` retain em dashes and are committed into run logs
- **Description**: [OUT_OF_SCOPE] `execution-issues.md` warning strings under `implement/` retain em dashes and are committed into run logs. Scenario: Post-fix run logs can still contain em dashes in warning lines even when run-summary renderers are clean; outside the issue’s `report/` and `git/` sweep scope
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/larch/implement/dispatch_step2.py:576
- **Phase**: design



