### FINDING_1: risk-integration: CHANGELOG.md:8-12
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] 34.0.6 changelog lists only #2511 while the branch also changes run-log required-files for optional oos-issues.ndjson (#2522). Consumers and triage read 34.0.6 notes and see no mention of the audit/manifest relaxation that actually shipped in the same version bump. Add a #2522 bullet (or split version bumps per concern) so changelog matches merged behavior.
- **Suggested revision**: Address the concern above.

### FINDING_2: risk-integration: merge-base..HEAD
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Three stacked commits mix redact_gh_error hardening, run-log manifest change, and a large larch-logs flush. Bisect and plan-fidelity review cost rise because unrelated change sets share one branch and one PATCH version. Split PRs or explicitly enumerate every shipped change in changelog/PR body.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/clarify-comment-post.sh:2269-2286 (mirrored)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Identical truncation-marker case arms are duplicated across several scripts alongside parallel write/read variants. Future edits to truncation semantics can drift across copies with partial CI coverage. Extract one shared redact_gh_error helper or single sourced implementation.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] risk-integration: scripts/tracking-issue-read.sh:2787-2798
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Scrubber stderr is discarded via 2>/dev/null on read paths. WARN visibility gap called out in bundled prior review; not introduced solely by the new truncation case. Track as separate observability work if WARN lines must surface.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: scripts/clarify-comment-post.sh:2271-2278
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Inconsistent generic ERROR= wording vs tracking-issue-write tests (gh stderr vs gh failure prefixes). Legacy string divergence; truncation hunks do not obviously create the mismatch. Normalize messages in a dedicated consistency follow-up if desired.
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: CHANGELOG.md:8-12
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] 34.0.6 changelog documents only #2511 while the same release ships #2522 required-files manifest change. Operators reading Keep a Changelog entries miss that required-file-presence no longer treats oos-issues.ndjson as mandatory. Add a #2522 bullet under [34.0.6] or split version entries so notes match all shipped behavior.
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: ad2c818a..436e9294
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Branch bundles #2511 redact_gh_error hardening with #2522 run-log manifest tweak plus larch-logs flush commits. A CI regression or production revert in one area blocks unrelated changes and complicates bisect. Split PRs by concern or document intentional batching with explicit validation for each thread.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: scripts/test-verify-run-log-completeness.sh:148-184
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No harness case covers step9a1 reached via oos-issues.ndjson alone while run-statistics.md is still missing. A future edit to condition_reached or TSV parsing could accidentally waive run-statistics when oos exists; CI would not lock that interaction. Add a fixture asserting MISSING includes run-statistics.md when only oos-issues satisfies step9a1 signals.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: #2522 implementation_plan Verification
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan mandates make test-verify-run-log-completeness and make lint; diff alone does not evidence green runs on the combined tree. Merged PR could still fail CI or local lint if commands were not run after final rebases. Ensure CI passes on the PR and optionally paste check output for reviewers.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: docs/run-logs-required-files.tsv:175
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Required-file manifest no longer lists oos-issues.ndjson so required-file-presence cannot fail solely for a missing OOS NDJSON batch when step9a1 is otherwise satisfied. A run with OOS work reflected only in summaries could omit the durable NDJSON batch yet pass the scan if run-statistics.md and other required rows exist. Add a dedicated conditional scan or document the weaker invariant; do not restore blanket required-file false positives without another signal.
- **Suggested revision**: Address the concern above.

### FINDING_11: security: scripts/tracking-issue-write.sh:229-234
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Truncation fail-closed path keys off a loose substring of the redactor’s marker text. If redact-secrets rewords the marker, stderr might pass the case guard while still carrying sensitive material. Align marker text with a single contract and regression-test the substring pairing.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/clarify-comment-post.sh:41-44 vs scripts/tracking-issue-write.sh:222-227
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Inconsistent generic ERROR strings across helpers for the same redaction failure modes. Operators or automation grepping one phrase miss failures emitted by another helper. Normalize generic strings or centralize the helper.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: CHANGELOG.md:8-12
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Changelog 34.0.6 cites only #2511 while other user-visible changes ship in the same version. Consumers relying on CHANGELOG miss the run-log audit policy change and related work. Add bullets or split releases.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] risk-integration: scripts/clarify-comment-post.sh:17
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Gh stderr redaction uses secrets-only pipeline, not tmpdir+secrets chain like tracking-issue-write. Path-shaped sensitive material in gh API errors may be less thoroughly scrubbed than on write paths. Pre-existing asymmetry; not introduced by the truncation guard hunk.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] security: scripts/tracking-issue-read.sh:123
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Scrubber stderr discarded via 2>/dev/null hides WARN visibility. Operational blind spot for PEM truncation warnings on read paths. Pre-existing; unchanged intent of this diff hunk.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: CHANGELOG.md:8-12
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] 34.0.6 changelog lists only #2511 while the same release ships #2522 run-log required-file / harness changes. Operators and downstream release readers can miss that oos-issues.ndjson is no longer a required-file-presence / verify-run-log-completeness requirement. Add a 34.0.6 bullet for the run-log manifest / verification change (#2522) or split version entries.
- **Suggested revision**: Address the concern above.

### FINDING_17: architecture: scripts/tracking-issue-write.sh:222-235;scripts/tracking-issue-read.sh:115-135;scripts/clarify-comment-post.sh:2269-2287;scripts/clarify-label.sh:2320-2338;scripts/clarify-state.sh:2371-2389;scripts/plan-block-read.sh:2422-2440;scripts/plan-block-write.sh:2473-2491
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Parallel copies of redact_gh_error each gained the same truncation-marker guard. Future one-off edits to marker text or control flow can diverge across helpers and reintroduce inconsistent stderr redaction or exit envelopes. Centralize redact_gh_error in one sourced lib or add a CI diff guard across copies.
- **Suggested revision**: Address the concern above.

### FINDING_18: code-quality: scripts/tracking-issue-write.sh:226-227;scripts/clarify-*.sh;scripts/plan-block-*.sh;scripts/tracking-issue-read.sh:118-119
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Inconsistent generic ERROR strings across redact_gh_error copies after fail-closed hardening. Aggregators and operators cannot rely on one stable token for all gh stderr redaction failures. Normalize literals or document per-script prefixes in SECURITY.md.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] risk-integration: merge-base..HEAD
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Multi-issue branch stacks #2511 #2522 and larch-logs flush. Bisect and review noise versus single-concern branches. Prefer single-issue branches or enumerate all shipped changes in CHANGELOG when stacking.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] risk-integration: scripts/tracking-issue-read.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] redact-secrets stderr discarded via 2>/dev/null on read path. WARN visibility for PEM truncation remains hidden; pre-existing observability gap. Separate follow-up if WARN visibility on reads is required.
- **Suggested revision**: Address the concern above.

### FINDING_21: **Important** **risk-integration** `merge-base(HEAD,main)..HEAD` — The supplied implementation plan only describes issue **#2522** (TSV row removal, two test assertions, `audit-scan-run.md` example, `docs/run-logs.md` wording, and verification), but `git log merge-base..HEAD` shows **three** commits: `ad2c818a` (**#2511** `redact_gh_error` hardening across multiple `scripts/*.sh`, `scripts/tracking-issue-write.md`, `scripts/test-tracking-issue-write.sh`, `SECURITY.md`), `909ef806` (run-logs / **#2522**), and `436e9294` (`chore(larch-logs)` flush). The diff also bumps `.claude-plugin/plugin.json` to **34.0.6** and extends `CHANGELOG.md` for **#2511**, none of which appear in the #2522 plan text. **Suggested fix:** For Plan Fidelity sign-off, either narrow the reviewed diff to the #2522 commit (or a PR that contains only that change set) or supply an additional plan that covers #2511, the version bump, and any other non-#2522 surfaces so every changed path is traceable.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Important** **risk-integration** `merge-base(HEAD,main)..HEAD` — The supplied implementation plan only describes issue **#2522** (TSV row removal, two test assertions, `audit-scan-run.md` example, `docs/run-logs.md` wording, and verification), but `git log merge-base..HEAD` shows **three** commits: `ad2c818a` (**#2511** `redact_gh_error` hardening across multiple `scripts/*.sh`, `scripts/tracking-issue-write.md`, `scripts/test-tracking-issue-write.sh`, `SECURITY.md`), `909ef806` (run-logs / **#2522**), and `436e9294` (`chore(larch-logs)` flush). The diff also bumps `.claude-plugin/plugin.json` to **34.0.6** and extends `CHANGELOG.md` for **#2511**, none of which appear in the #2522 plan text. **Suggested fix:** For Plan Fidelity sign-off, either narrow the reviewed diff to the #2522 commit (or a PR that contains only that change set) or supply an additional plan that covers #2511, the version bump, and any other non-#2522 surfaces so every changed path is traceable.
- **Suggested revision**: Address the concern above.

### FINDING_22: **Latent** **risk-integration** `implementation plan — Verification` — The plan requires `make test-verify-run-log-completeness` and `make lint`; the diff and review bundle do not include command output or CI artifacts proving those steps were run and passed. **Suggested fix:** Rely on mandatory PR checks and/or paste transcript links in the PR so the verification requirement is evidenced without assuming local runs.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Latent** **risk-integration** `implementation plan — Verification` — The plan requires `make test-verify-run-log-completeness` and `make lint`; the diff and review bundle do not include command output or CI artifacts proving those steps were run and passed. **Suggested fix:** Rely on mandatory PR checks and/or paste transcript links in the PR so the verification requirement is evidenced without assuming local runs. **#2522 plan traceability (summary):** The diff implements all four enumerated edits: [`docs/run-logs-required-files.tsv`](docs/run-logs-required-files.tsv) drops the `oos-issues.ndjson` row; [`scripts/test-verify-run-log-completeness.sh`](scripts/test-verify-run-log-completeness.sh) removes the two `oos-issues.ndjson` `MISSING` assertions; [`.claude/skills/audit-runs/scripts/audit-scan-run.md`](.claude/skills/audit-runs/scripts/audit-scan-run.md) replaces the example `missing` entry so it no longer lists `oos-issues.ndjson`; [`docs/run-logs.md`](docs/run-logs.md) updates `run-statistics.md` “Written” text while keeping the `### oos-issues.ndjson` section. There is no diff touching `scripts/verify-run-log-completeness.sh` or `.claude/skills/audit-runs/scripts/audit-scan-run.sh`, matching the plan’s “do not change OR-checks” constraint. ```tsv schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix 1	in_scope	important	risk_integration	merge-base(HEAD,main)..HEAD	Branch bundles #2511 redact_gh_error work, 34.0.6 plugin bump, CHANGELOG, and larch-logs flush in addition to the #2522 plan	A reviewer using only the #2522 plan cannot walk requirement-by-requirement over the full branch-vs-main diff	Narrow the reviewed diff to the #2522 commit or add a covering plan for every extra change set 1	in_scope	latent	risk_integration	implementation plan Verification	Plan mandates make test-verify-run-log-completeness and make lint	Static diff provides no proof those commands succeeded	Evidence via CI or pasted command output in the PR ```
- **Suggested revision**: Address the concern above.

