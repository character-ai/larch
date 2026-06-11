# scripts/redact-secrets.sh — contract

`scripts/redact-secrets.sh` is the shell outbound secret-scrubbing filter for bash call sites that still pipe through it (for example `/issue` Step 4.0 probe stderr sanitization in `skills/issue/SKILL.md`). `python/cli.py issue create-one` uses `python/redact.py` instead. Regression coverage: `scripts/test-redact-secrets.sh` (`make test-redact`) for the shell filter, and `python/test_redact.py` plus `python/test_issue_create.py` (`make py-test`) for the Python path. Edit patterns only after reading `SECURITY.md`'s outbound-redaction subsection.

Timing reports are designed to avoid a path-redaction dependency: `scripts/timing-ledger.sh` records only `basename(output)` for vendor task rows, and `scripts/timing-report.sh` does not render an output-path column. Public timing-report fragments therefore do not expose absolute workspace or session-tmpdir paths.
