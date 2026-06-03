# scripts/scrub-log-secrets.sh — contract

`scripts/scrub-log-secrets.sh <dir>` is the pre-flush secret gate run before
every larch run-log commit. It scans every file under `<dir>` (NO path
exclusions), scrubs secret-shaped values in place, and emits a very loud
`larch_err` banner plus the `LARCH_SECRET_SCRUB_VIOLATIONS` /
`LARCH_SECRET_SCRUB_FILES` stdout contract when it redacts anything. Files with
no secret are left byte-for-byte untouched. The flush proceeds with the
redacted content (exit `0`); the gate exits non-zero only fail-closed — `2` for
a bad argument or a missing `redact-secrets.sh`, `3` when a file cannot be
scrubbed or a detected secret survives scrubbing — so the caller aborts rather
than committing an unscrubbed secret.

It is larch's own scrubber, so consumer repos need no third-party secret
scanner installed for the run-log flush to be safe.

## Coverage

- Cursor API keys (`crsr_…` and `key_…`) — the incident class; NOT covered by
  `redact-secrets.sh`.
- Slack, Google API, Stripe live, and GitLab PAT prefixes.
- As a backstop, the families `redact-secrets.sh` already covers (sk-/sk-ant-,
  GitHub tokens, AWS AKIA, JWT, PEM private keys) — scrubbed by piping through
  `redact-secrets.sh`; the extra families by an additional `sed -E` pass
  derived from the same regex table used for detection (single source of truth).

## Callers

- `scripts/larch-log.sh` (`commit` subcommand) — implement / review / research
  flush.
- `scripts/design-log-publish.sh` — `/design` flush.

Both capture the gate's stdout and surface `SECRET_SCRUB_VIOLATIONS` to the
operator: `/design` via `skills/design/scripts/design-publish.sh` `add_warn`;
`/implement` via `scripts/larch-log-flush.sh` and
`skills/implement/scripts/step-7a.sh`. Python parity for the in-progress
`ship-pr` rework lives in `python/run_logs.py` (`_scrub_run_tree`, called from
`_larch_log_commit`) and `python/redact.py` (`scrub_log_secrets`).

## Edit-in-sync

- Keep the base-family detection regexes in sync with `scripts/redact-secrets.sh`.
- Keep the extra-family regexes in sync with `python/redact.py`
  (`_EXTRA_SECRET_FAMILIES`).
- `scripts/test-scrub-log-secrets.sh` is the regression harness, wired into
  `make lint` via the `test-scrub-log-secrets` target.
- `scrub-log-secrets.sh` and `test-scrub-log-secrets.sh` are allowlisted in
  `.gitleaks.toml` (they carry regex patterns and synthetic fixtures, not real
  secrets); `larch-logs/**` is deliberately NOT allowlisted.
- See `SECURITY.md` ("Layered secret scanning") for how this gate relates to the
  gitleaks/trufflehog layers.
