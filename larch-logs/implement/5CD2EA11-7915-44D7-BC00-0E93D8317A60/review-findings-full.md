### FINDING_1: panel [code-review/accepted]

## **Important** `security` `larch-logs/implement/D1984F57-A5A7-4632-8114-6533205051D3/round-1/codex-generalist-output.txt.meta:8` — The committed run logs still expose an unredacted operator-local repo path via `OUTER_LAUNCHER_WORKDIR`; the same leak pattern appears in multiple `round-1/*output.txt.meta` files and in `larch-logs/implement/D1984F57-A5A7-4632-8114-6533205051D3/round-1/coder-prompt.md:11`. Concrete scenario: this PR is merged and ships public `larch-logs/implement/...` artifacts containing the operator’s local home/repo path, which is the privacy leak class called out in the feature description. Scrub the committed log files before merge and update `scripts/redact-tmpdir-paths.sh` to redact `/Users/<user>/<repo>` or `/home/<user>/<repo>` when the repo path appears at end-of-value/end-of-line or before punctuation, then add a regression case for `OUTER_LAUNCHER_WORKDIR=/Users/name/repo`.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `security` `larch-logs/implement/D1984F57-A5A7-4632-8114-6533205051D3/round-1/codex-generalist-output.txt.meta:8` — The committed run logs still expose an unredacted operator-local repo path via `OUTER_LAUNCHER_WORKDIR`; the same leak pattern appears in multiple `round-1/*output.txt.meta` files and in `larch-logs/implement/D1984F57-A5A7-4632-8114-6533205051D3/round-1/coder-prompt.md:11`. Concrete scenario: this PR is merged and ships public `larch-logs/implement/...` artifacts containing the operator’s local home/repo path, which is the privacy leak class called out in the feature description. Scrub the committed log files before merge and update `scripts/redact-tmpdir-paths.sh` to redact `/Users/<user>/<repo>` or `/home/<user>/<repo>` when the repo path appears at end-of-value/end-of-line or before punctuation, then add a regression case for `OUTER_LAUNCHER_WORKDIR=/Users/name/repo`.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## correctness: docs/run-logs.md (manifest.json section)

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] New doc claims committed manifest status is always "in-progress". Other lifecycle docs describe partial/stalled manifest tagging under tmpdir-driven recovery; an absolute "always" can mislead readers if a non-in-progress snapshot were ever flushed. Soften to "normally" or enumerate exceptions and link to the manifest contract.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## correctness: docs/run-logs.md (manifest.json section, new status paragraph)

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New docs claim committed manifest status is always in-progress and done exists only post-merge in tmpdir. Contradicts many committed larch-logs/implement/*/manifest.json files with status done (e.g. larch-logs/implement/FA318108-514A-405E-B331-3664A952C94A/manifest.json:10); misleads consumers auditing the tree. Reword to match actual committed corpus and lifecycle (legacy done vs current intent), or document the transition explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## correctness: docs/run-logs.md:71-73

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] New paragraph claims committed manifest status is always in-progress; adjacent line still says final run status; manifest subcommand allows status updates. Operator or test runs manifest --field status=done then commit; committed JSON shows done contradicting always in-progress. Rewrite to describe typical implement flush snapshots; allow exceptions; align line 71 wording.
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## correctness: docs/run-logs.md:73

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New paragraph claims committed manifest status is always in-progress and done is never committed. Contradicts many existing committed larch-logs/implement/*/manifest.json files with status done; operators or tools may encode a false invariant. Reword to match observed committed data and SKILL/larch-log contracts, or narrow the claim to the intended lifecycle window.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## correctness: docs/run-logs.md:73

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Committed manifest status documented as always "in-progress" Readers infer committed status is a complete lifecycle truth; contradicts recovery paths that can set e.g. partial before a flush, so operational and audit conclusions about a run can be wrong Replace absolute "always" with accurate lifecycle wording; enumerate or defer to scripts/larch-log.md for committed vs tmpdir-only statuses
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## risk-integration: scripts/ship-pr.sh:397-421

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] rewrite_reasoning_new_version treats awk success as rewrite success even when the New version line never matched. Template drift leaves stale New version while bump and PR title use corrected semver; version-bump-reasoning batch can still lie. Verify corrected line exists after awk (grep/cmp) and return failure to trigger existing WARN path when rewrite was a no-op.
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## code-quality: docs/run-logs.md:71-73

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Adjacent prose suggests manifest holds final status while next line says committed status is always in-progress Readers treat the section as contradictory and mistrust one of the two statements Qualify the first sentence so live schema vs committed snapshot is explicit
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## code-quality: scripts/test-larch-log.sh:188-212

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale-run test depends on $_cpayload from the prior subtest Reordering or deleting the earlier block breaks this test with unclear failure Define payload inside the stale block or document the coupling explicitly
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## **Important** `security` `scripts/redact-tmpdir-paths.sh:20` — The new operator-path redaction regex treats any punctuation as the end of the repo directory, so valid repo names containing punctuation are only partially redacted. Concrete scenario: `<OPERATOR_REPO_PATH>/scripts/foo.sh` now becomes `<OPERATOR_REPO_PATH>+repo/scripts/foo.sh`, while the previous slash-terminated rule redacted it to `<OPERATOR_REPO_PATH>/scripts/foo.sh`; committed logs can still expose operator repo-name fragments and suffix paths. Restore the broader component match for slash-terminated paths and add coverage for punctuation-bearing repo names, then handle root-before-punctuation as a separate case that does not split inside valid directory names.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `security` `scripts/redact-tmpdir-paths.sh:20` — The new operator-path redaction regex treats any punctuation as the end of the repo directory, so valid repo names containing punctuation are only partially redacted. Concrete scenario: `<OPERATOR_REPO_PATH>/scripts/foo.sh` now becomes `<OPERATOR_REPO_PATH>+repo/scripts/foo.sh`, while the previous slash-terminated rule redacted it to `<OPERATOR_REPO_PATH>/scripts/foo.sh`; committed logs can still expose operator repo-name fragments and suffix paths. Restore the broader component match for slash-terminated paths and add coverage for punctuation-bearing repo names, then handle root-before-punctuation as a separate case that does not split inside valid directory names.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## correctness: scripts/redact-tmpdir-paths.sh:2714-2717

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Operator path regex segments narrowed to [[:alnum:]_.-]+ vs former [^/"[:space:]]+. Path like <OPERATOR_REPO_PATH>/... no longer matches; operator path can leak into committed or published logs. Widen segment charset (e.g. include +) or document and test; keep EOL/punctuation behavior.
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## correctness: scripts/ship-pr.sh:1238-1241

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] new_version passed to semver_lt without same strict semver regex as _origin_ver. Malformed NEW_VERSION from classify/parsing can make numeric compares wrong or unpredictable for regression guard. Validate new_version with ^[0-9]+.[0-9]+.[0-9]+$ before semver_lt or fail closed.
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## risk-integration: scripts/ship-pr.sh:1252-1289

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Rewrite failure is non-fatal but larch-log write still ingests uncorrected reasoning_file. Awk or grep validation fails; version-bump-reasoning batch still shows pre-correction NEW_VERSION while plugin.json and PR title show corrected bump. Gate larch-log write on successful rewrite, inject synthetic correction content, or stall until reconciled.
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## security: scripts/redact-tmpdir-paths.sh:20-21

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Operator path redaction now matches only [alnum._-] per path segment; some valid path characters no longer match the full segment. Example <OPERATOR_REPO_PATH>/repo/... can partially match and rewrite to a corrupted line while leaving +bar/repo... unredacted. Widen segment class safely or layer patterns; add regression tests for + and similar filename characters.
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## security: scripts/redact-tmpdir-paths.sh:20-21

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Operator path segments restricted to [[:alnum:]_.-]+ vs prior broader class. Unusual clone directory names may no longer redact and could leak into published artifacts. Add tests or widen allowed characters without breaking boundaries.
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## security: scripts/redact-tmpdir-paths.sh:2714-2717

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Narrow ASCII-only path segments and locale-sensitive alnum for operator-repo redaction. Operator home or repo dir names with characters outside [[:alnum:]_.-] or locale quirks can leave literal /Users/... or /home/... paths in published text despite SECURITY.md claiming broader coverage. Document ASCII-only assumption set LC_ALL=C at scrubber entry or add a conservative second pass for /Users and /home prefixes.
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## code-quality: scripts/larch-log.sh:430-432

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Comment cites LARCH_LOG_REPO_ROOT vs REPO_ROOT symlink mismatch though both roots come from the same rev-parse at load. Maintainers chase the wrong root-cause story when debugging pathspec issues. Reword comment to describe prefix/pathspec hardening accurately.
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## **Important** `security` `scripts/redact-tmpdir-paths.sh:21-24` — The new bare operator-repo-root redaction still misses quoted JSON/string values, so a common committed-log shape remains unredacted. Concrete scenario: `{"cwd":"/Users/example/my.repo"}` passes through `scripts/redact-tmpdir-paths.sh` unchanged, leaking the operator username and repo path despite the new `SECURITY.md` guarantee for end-of-value repo roots. Extend the delimiter handling to capture and preserve quotes/JSON separators, and add regression tests in `scripts/test-redact-tmpdir-paths.sh` for quoted JSON values like `{"cwd":"/Users/example/my.repo"}` and `{"cwd":"/Users/example/my.repo","x":1}`.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `security` `scripts/redact-tmpdir-paths.sh:21-24` — The new bare operator-repo-root redaction still misses quoted JSON/string values, so a common committed-log shape remains unredacted. Concrete scenario: `{"cwd":"/Users/example/my.repo"}` passes through `scripts/redact-tmpdir-paths.sh` unchanged, leaking the operator username and repo path despite the new `SECURITY.md` guarantee for end-of-value repo roots. Extend the delimiter handling to capture and preserve quotes/JSON separators, and add regression tests in `scripts/test-redact-tmpdir-paths.sh` for quoted JSON values like `{"cwd":"/Users/example/my.repo"}` and `{"cwd":"/Users/example/my.repo","x":1}`.
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## risk-integration: scripts/ship-pr.sh:773-781

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] run_bump_phase maps only same-version apply-bump ERROR to exit 5; new version regression ERROR hits exit_stall 8 First bump after CI can stall at Step 8 when NEW_VERSION < origin/main even though run_rebase_rebump auto-corrects the same condition later; asymmetric recovery vs same-version race Extend case arm for version regression ERROR to same Exit 5 / sub-procedure routing or apply semver correction before apply-bump in run_bump_phase
- **Suggested revision**: Address the concern above.

