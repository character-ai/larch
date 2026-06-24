# test-render-cost-line-callsites.sh

Callsite lint for final-summary top-chat contracts. It pins the `/implement`
Step 17/18 `write-final-report.sh --print-stdout` guards, the shared-profile
full-body exception prose, and the `/design`
`render-final-summary --post-publish-only` full-body emit contract.

The common emit contract pins live in `skills/shared/final-summary-emit.md`.
The harness asserts the marker-first profile is parameterized by caller marker
tokens, task-output source, Read fallback policy, and sidecar policy. It also
keeps the shared prohibitions on task-output re-reads and Bash/Python marker
scraping.

`skills/design/SKILL.md` keeps only site-specific gates and binding glue. The
harness pins Step 0b cancel routes to the file-only profile, keeps the
post-publish gates in Step 5c/5d, checks marker-first design callsites bind
`LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` plus
`<task-notification>` sources, and rejects reintroduced full marker-extraction
procedure prose in the design skill.

The `python3 python/cli.py token render-cost-line` allowlist remains deliberately
scoped to the deprecated standalone helper. This harness also negative-greps the
active SKILL.md files so cost-line-only orchestrator prose cannot be
reintroduced.
