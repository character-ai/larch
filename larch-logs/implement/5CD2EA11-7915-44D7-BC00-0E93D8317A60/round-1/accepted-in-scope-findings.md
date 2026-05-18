### FINDING_1: **Important** `security` `larch-logs/implement/D1984F57-A5A7-4632-8114-6533205051D3/round-1/codex-generalist-output.txt.meta:8` — The committed run logs still expose an unredacted operator-local repo path via `OUTER_LAUNCHER_WORKDIR`; the same leak pattern appears in multiple `round-1/*output.txt.meta` files and in `larch-logs/implement/D1984F57-A5A7-4632-8114-6533205051D3/round-1/coder-prompt.md:11`. Concrete scenario: this PR is merged and ships public `larch-logs/implement/...` artifacts containing the operator’s local home/repo path, which is the privacy leak class called out in the feature description. Scrub the committed log files before merge and update `scripts/redact-tmpdir-paths.sh` to redact `/Users/<user>/<repo>` or `/home/<user>/<repo>` when the repo path appears at end-of-value/end-of-line or before punctuation, then add a regression case for `OUTER_LAUNCHER_WORKDIR=/Users/name/repo`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `security` `larch-logs/implement/D1984F57-A5A7-4632-8114-6533205051D3/round-1/codex-generalist-output.txt.meta:8` — The committed run logs still expose an unredacted operator-local repo path via `OUTER_LAUNCHER_WORKDIR`; the same leak pattern appears in multiple `round-1/*output.txt.meta` files and in `larch-logs/implement/D1984F57-A5A7-4632-8114-6533205051D3/round-1/coder-prompt.md:11`. Concrete scenario: this PR is merged and ships public `larch-logs/implement/...` artifacts containing the operator’s local home/repo path, which is the privacy leak class called out in the feature description. Scrub the committed log files before merge and update `scripts/redact-tmpdir-paths.sh` to redact `/Users/<user>/<repo>` or `/home/<user>/<repo>` when the repo path appears at end-of-value/end-of-line or before punctuation, then add a regression case for `OUTER_LAUNCHER_WORKDIR=/Users/name/repo`.
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: docs/run-logs.md (manifest.json section)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] New doc claims committed manifest status is always "in-progress". Other lifecycle docs describe partial/stalled manifest tagging under tmpdir-driven recovery; an absolute "always" can mislead readers if a non-in-progress snapshot were ever flushed. Soften to "normally" or enumerate exceptions and link to the manifest contract.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: docs/run-logs.md (manifest.json section, new status paragraph)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New docs claim committed manifest status is always in-progress and done exists only post-merge in tmpdir. Contradicts many committed larch-logs/implement/*/manifest.json files with status done (e.g. larch-logs/implement/FA318108-514A-405E-B331-3664A952C94A/manifest.json:10); misleads consumers auditing the tree. Reword to match actual committed corpus and lifecycle (legacy done vs current intent), or document the transition explicitly.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: docs/run-logs.md:71-73
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] New paragraph claims committed manifest status is always in-progress; adjacent line still says final run status; manifest subcommand allows status updates. Operator or test runs manifest --field status=done then commit; committed JSON shows done contradicting always in-progress. Rewrite to describe typical implement flush snapshots; allow exceptions; align line 71 wording.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: docs/run-logs.md:73
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New paragraph claims committed manifest status is always in-progress and done is never committed. Contradicts many existing committed larch-logs/implement/*/manifest.json files with status done; operators or tools may encode a false invariant. Reword to match observed committed data and SKILL/larch-log contracts, or narrow the claim to the intended lifecycle window.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: docs/run-logs.md:73
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Committed manifest status documented as always "in-progress" Readers infer committed status is a complete lifecycle truth; contradicts recovery paths that can set e.g. partial before a flush, so operational and audit conclusions about a run can be wrong Replace absolute "always" with accurate lifecycle wording; enumerate or defer to scripts/larch-log.md for committed vs tmpdir-only statuses
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: scripts/ship-pr.sh:397-421
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] rewrite_reasoning_new_version treats awk success as rewrite success even when the New version line never matched. Template drift leaves stale New version while bump and PR title use corrected semver; version-bump-reasoning batch can still lie. Verify corrected line exists after awk (grep/cmp) and return failure to trigger existing WARN path when rewrite was a no-op.
- **Suggested revision**: Address the concern above.


### FINDING_7: code-quality: docs/run-logs.md:71-73
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Adjacent prose suggests manifest holds final status while next line says committed status is always in-progress Readers treat the section as contradictory and mistrust one of the two statements Qualify the first sentence so live schema vs committed snapshot is explicit
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: scripts/test-larch-log.sh:188-212
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale-run test depends on $_cpayload from the prior subtest Reordering or deleting the earlier block breaks this test with unclear failure Define payload inside the stale block or document the coupling explicitly
- **Suggested revision**: Address the concern above.


