# test-render-cost-line-callsites.sh

Callsite lint for final-summary top-chat contracts. It pins the `/implement`
Step 17/18 `write-final-report.sh --print-stdout` guards, the shared-profile
full-body exception prose, and the `/design`
`render-final-summary --post-publish-only` full-body emit contract.

The common emit contract pins live in `skills/shared/final-summary-emit.md`.
The harness asserts the marker-first profile is parameterized by caller marker
tokens, task-output source, Read fallback policy, and sidecar policy. It also
keeps the shared prohibitions on task-output re-reads, Bash/Python marker
scraping, post-emit recap prose, and approximate no-cost paraphrases.

`skills/design/SKILL.md` keeps only site-specific gates, source names, and
shared-row citations. The harness pins Step 0b cancel routes to the file-only
profile, the non-empty `FINAL_SUMMARY_PATH` gate, the retained
`design-step-final-summary.sh` and `design-step5c.sh` source names, and the
`/design` marker-first row cite at each emit site. It also pins the
render-exit carve-out phrase **Not** gated on `python/cli.py design
render-final-summary` exit 0 in both the always-loaded preamble and Step 5c
item 5.

Gantt and verbatim preservation are owned by `skills/shared/final-summary-emit.md`
Shared rules and the always-loaded `/design` preamble stub. The design callsite
checks therefore prefer source-name, shared-row, ordering, and negative-grep
tokens over per-site inline Gantt paragraph scans. The harness rejects
reintroduced full marker-extraction procedure prose and repeated long
`Binding: markers ...` restatements in the design skill.

The `python3 python/cli.py token render-cost-line` allowlist remains deliberately
scoped to the deprecated standalone helper. This harness also negative-greps the
active SKILL.md files so cost-line-only orchestrator prose cannot be
reintroduced.
