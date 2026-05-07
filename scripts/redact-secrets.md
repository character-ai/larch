# scripts/redact-secrets.sh — contract

`scripts/redact-secrets.sh` is the outbound secret-scrubbing filter invoked by `skills/issue/scripts/create-one.sh` before `gh issue create`. `scripts/test-redact-secrets.sh` is its regression test, wired into `make lint` via the `test-redact` target. Edit patterns only after reading `SECURITY.md`'s outbound-redaction subsection.

Timing reports are designed to avoid a path-redaction dependency: `scripts/timing-ledger.sh` records only `basename(output)` for vendor task rows, and `scripts/timing-report.sh` does not render an output-path column. Public timing-report fragments therefore do not expose absolute workspace or session-tmpdir paths.
