### FINDING_1: code-quality: scripts/design-log-publish.sh:254-311
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] ~55-line design_publish_breadcrumbs duplicates larch_log_publish_breadcrumbs in scripts/larch-log.sh:156-212 Redaction or fail-closed rule changes must be edited twice; paths can drift (e.g. error text exit codes) Extract one shared publish helper and call it from larch-log.sh commit and design-log-publish.sh
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/test-breadcrumb-monitor.sh:237-434
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Plan-required partial-byte and redactor fail-closed tests are missing from expanded harness Monitor partial-line buffering and WARN redact-drop-line regressions ship without offline detection Add partial-line and stubbed lib-redact-streaming non-zero tests per plan FINDING_25
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/test-lib-quiet.sh:1-134
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] No tests for emit_breadcrumb_stderr stream-set vs stream-unset paths scripts/lib-quiet.sh:267-295 ci-wait bridge can break while make test-lib-quiet still passes Add stream-file and larch_errf no-newline assertions for emit_breadcrumb_stderr
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/test-ci-wait.sh:1-238
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] No LARCH_BREADCRUMB_STREAM variant asserting c=wait-ci records Stream-set ci-wait progress may stop writing structured breadcrumbs with no harness signal Add temp stream export and grep for c=wait-ci with stderr contract checks
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/test-larch-log.sh:221-244
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Fail-closed breadcrumb test covers symlink only not redactor failure redact-secrets.sh --streaming non-zero could leave partial breadcrumbs/ on other inputs Add harness that forces redactor non-zero and asserts no larch-logs/.../breadcrumbs/
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/larch-log.sh:562-578
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Mis-shaped --log-root skips breadcrumbs silently via larch_log_breadcrumb_source_dir || true Non-standard log roots with live session breadcrumbs/ never commit streams without warning Warn or fail when breadcrumbs exist under session tmpdir but source resolution fails
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/lib-quiet.md:20-30
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Docs omit LARCH_BREADCRUMB_STREAM and mandatory --category= vocabulary Authors may migrate callsites without categories and get dropped stream records Document stream contract and valid categories alongside emit_breadcrumb_stderr
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/test-breadcrumb-monitor-bash32.sh:22
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Bash32 harness re-execs tests without byte-for-byte parity assertion Plan wording implies diff vs default bash run; only skip-or-run is implemented Document parity as re-exec only or capture and diff outputs from both shells
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/ship-pr.sh:2160-2161
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Double emit_breadcrumb for one Phase 1-4 handoff (stall then escalate) Monitor shows duplicate warnings for one event; category filters see two records Use single category per handoff unless downstream requires both
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] code-quality: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Uncategorized emit_breadcrumb predates this branch Under LARCH_BREADCRUMB_STREAM records are dropped with unknown-category warning Migrate apply-bump.sh when that path gets a breadcrumb stream
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] architecture: scripts/larch-log.sh:193
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Commit redaction inlines redact-secrets --streaming; monitor uses lib-redact-streaming.sh Two streaming redaction call styles can diverge on PEM/state handling Optionally pipe tmpdir-redacted input through lib-redact-streaming.sh in commit path
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/test-ci-wait.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Plan-mandated LARCH_BREADCRUMB_STREAM-set ci-wait regression is absent Stream-set regressions that write progress to stdout instead of the breadcrumb stream pass make test-ci-wait but break breadcrumb-monitor pairing during backgrounded ci-wait Add a stubbed harness case with LARCH_BREADCRUMB_STREAM set: assert stream contains c=wait-ci and stderr lacks progress-tier lines
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/test-lib-quiet.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] No tests for emit_breadcrumb_stderr stream-set vs stream-unset paths A bad stream-unset branch (e.g. emit instead of larch_errf) breaks byte-identical stderr dot progress without failing existing tests Add test-lib-quiet cases pinning stderr bytes when stream unset and larch:bc wait-ci records when stream set
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/test-breadcrumb-monitor.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Missing partial-byte retention and redactor fail-closed tests from FINDING_25 Monitor may emit partial larch:bc lines or leak raw content on redactor non-zero without regression signal Add mid-line write test (no emit until newline) and stub redactor non-zero test expecting WARN redact-drop-line and no raw secret
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/test-larch-log.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Missing fail-closed test when redact-secrets.sh --streaming exits non-zero during breadcrumb commit A broken streaming redactor could commit raw PEM while symlink and happy-path breadcrumb tests still pass Add fixture forcing non-zero streaming redactor exit; assert commit aborts and no larch-logs/.../breadcrumbs/ in repo
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/ci-wait.sh:254-255
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Bail summary migrated to emit_breadcrumb_stderr --category=wait-ci; plan kept bail tier on larch_err With LARCH_BREADCRUMB_STREAM set, ci-decide bail reason appears only as wait-ci breadcrumb not stderr; warn-filtered monitors miss it Keep bail summaries on larch_err/larch_errf or use --category=warn for bail lines
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/ship-pr.sh:2160
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] warn-prefixed message uses --category=stall Consumers surfacing only c=warn omit recovery-waterfall-exhausted stall-tagged line Use --category=warn per emoji-prefix routing or reword with stall emoji
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] architecture: scripts/design-log-publish.sh:254-312
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Duplicate breadcrumb publish pipeline vs larch_log_publish_breadcrumbs Future drift between design and implement publish semantics is possible but not a runtime bug today Extract shared helper when touching either path again
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] correctness: scripts/larch-log.sh:158
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Empty breadcrumb source skips publish without clearing existing repo_path/breadcrumbs Misconfigured log-root could leave stale breadcrumbs directory; standard IMPLEMENT_TMPDIR/larch-logs callers unaffected Document requirement or rm -rf destination when source resolution fails
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/test-ci-wait.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No LARCH_BREADCRUMB_STREAM / wait-ci stream assertions for emit_breadcrumb_stderr migration Under /implement with stream set, ci-wait progress is invisible in chat while stderr stays quiet; regressions in stream-set path pass CI Add stream-set poll case asserting ndjson c=wait-ci and empty progress stderr
- **Suggested revision**: Address the concern above.

### FINDING_21: security: scripts/larch-log.sh:127-212
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] larch_log_publish_breadcrumbs accepts LARCH_BREADCRUMB_SOURCE_DIR without session-tmpdir scope checks unlike breadcrumb-monitor.sh. A caller or compromised child exports LARCH_BREADCRUMB_SOURCE_DIR=/etc or $HOME/.config and larch-log commit ingests readable files into public larch-logs after partial redaction. Mirror larch_bm_under_session_tmp() (or equivalent realpath prefix check) before publishing; fail closed when override is outside IMPLEMENT/DESIGN/REVIEW/RESEARCH tmpdirs.
- **Suggested revision**: Address the concern above.

### FINDING_22: security: scripts/lib-quiet.sh:151-155
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Full-line 1KiB truncation can leave leading secret material in committed breadcrumb text=. A long API key or PEM-heavy line produces a committed larch:bc record whose first 1020 chars still contain recoverable secret prefix. Truncate only the text payload or drop oversized records with WARN instead of cut -c on the entire record.
- **Suggested revision**: Address the concern above.

### FINDING_23: security: scripts/ci-wait.sh:255,282
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] BAIL_REASON and suspend text use wait-ci category and enter committed breadcrumb streams. CI/gh failure strings (URLs, check names, internal repo hints) land in larch-logs/.../breadcrumbs/ on public repos despite PEM/tmpdir redaction. Use --category=warn for bail/suspend or keep those lines on larch_err only; extend SECURITY.md residual-risk note for wait-ci operational strings.
- **Suggested revision**: Address the concern above.

### FINDING_24: security: scripts/breadcrumb-monitor.sh:220-226
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Failure-tail redaction uses || true unlike per-line fail-closed drops. If lib-redact-streaming exits non-zero mid-tail, behavior is undefined vs silent omit; inconsistent with WARN redact-drop-line contract. Replace || true with explicit failure marker and no raw quiet-log bytes on redactor error; add harness assertion.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] security: scripts/lib-quiet.sh:176-181
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] EXIT trap chaining uses eval on captured trap body. Malicious trap injection if trap body were attacker-controlled (not introduced here). Out of scope; pre-existing pattern.
- **Suggested revision**: Address the concern above.

### FINDING_26: security: scripts/larch-log.sh:176-198
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Breadcrumb commit publishes every regular file under session breadcrumbs/ not only stream ndjson. Family B places .quiet .done .status and monitor sidecars beside .ndjson; flush commits quiet logs and control files contrary to docs/run-logs.md *.ndjson contract. Filter publish to *.ndjson or explicit allow-list; skip sentinel and monitor sidecar suffixes; mirror in design_publish_breadcrumbs.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: scripts/refresh-run-logs.sh:135-141
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Refresh masks larch-log commit failure and sets REFRESH_COMMITTED=true on any non-UNCHANGED stdout. Breadcrumb redaction failure exits commit non-zero but refresh reports success; push proceeds without committed breadcrumbs. Check commit exit code and LOG_WRITTEN/UNCHANGED; emit REFRESH_COMMITTED=false with ERROR on failure.
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: scripts/larch-log.sh:159-161
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Missing breadcrumb source deletes existing repo breadcrumbs/ directory. Late flush after tmpdir cleanup removes previously committed breadcrumb streams from the run log tree. No-op when source missing without rm -rf destination; only clear destination when source exists and filtered set is empty.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: scripts/test-larch-log.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Plan redactor fail-closed commit test not implemented. Redaction regression could allow partial breadcrumbs/ or silent publish bugs without CI signal. Add test forcing redact-secrets --streaming failure; assert non-zero commit and absent repo breadcrumbs/.
- **Suggested revision**: Address the concern above.

### FINDING_30: risk-integration: scripts/test-ci-wait.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No LARCH_BREADCRUMB_STREAM-set regression for emit_breadcrumb_stderr wait-ci records. Stream-set ci-wait progress could regress to stderr-only without harness detection. Add stream-set fixture asserting c=wait-ci in stream and stderr reserved for larch_err paths.
- **Suggested revision**: Address the concern above.

### FINDING_31: architecture: scripts/ci-wait.sh:255-282
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Bail/suspend lines use wait-ci category despite warning prefix. Monitor treats bail/suspend as CI-wait progress not warn for filtering/display. Use --category=warn for warning-prefixed emit_breadcrumb_stderr lines.
- **Suggested revision**: Address the concern above.

### FINDING_32: correctness: scripts/test-breadcrumb-monitor.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Partial-byte retention test from FINDING_25 is missing. During a mid-line stream write the monitor could emit a corrupted prefix or leak partial secrets without CI catching it. Add a test that writes an incomplete line, asserts silence, completes the line, then asserts full emission.
- **Suggested revision**: Address the concern above.

### FINDING_33: correctness: scripts/test-breadcrumb-monitor.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Redactor non-zero fail-closed test from FINDING_25 is missing. If lib-redact-streaming fails on a line the monitor might print raw stream content; no harness pins WARN redact-drop-line behavior. Stub the redactor to exit non-zero for one input line and assert warning plus no raw stdout.
- **Suggested revision**: Address the concern above.

### FINDING_34: correctness: scripts/test-larch-log.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Planned redactor-failure fail-closed commit test is not implemented. A broken streaming redactor could still leave partial larch-logs/.../breadcrumbs/ on disk; only symlink rejection is tested. Force redact-secrets --streaming to fail on a fixture file and assert commit aborts with no breadcrumbs directory.
- **Suggested revision**: Address the concern above.

### FINDING_35: correctness: scripts/test-ci-wait.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] No LARCH_BREADCRUMB_STREAM-set regression was added per plan testing strategy. c=wait-ci stream records and stderr suppression for progress tier are unverified; stream-set ci-wait could regress silently. Add a harness case with LARCH_BREADCRUMB_STREAM set; assert stream records and empty progress stderr.
- **Suggested revision**: Address the concern above.

### FINDING_36: correctness: scripts/test-lib-quiet.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] emit_breadcrumb_stderr stream-set and stream-unset paths are untested. The helper could break larch_errf no-newline semantics or stream formatting without CI signal. Add test-lib-quiet cases for both paths with byte and stream assertions.
- **Suggested revision**: Address the concern above.

### FINDING_37: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Uncategorized emit_breadcrumb under ship-pr inherited LARCH_BREADCRUMB_STREAM. Version-bump retry breadcrumbs are dropped with WARN unknown-category during Step 8 ship-pr. Use emit_breadcrumb --category=retry (or progress) on the apply-bump retry line.
- **Suggested revision**: Address the concern above.

### FINDING_38: architecture: agent-lint.toml
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Planned allow-list entry for scripts/lib-redact-streaming.md is missing. agent-lint may flag the new sibling md as unreachable depending on graph rules. Add scripts/lib-redact-streaming.md to exclude with the breadcrumb harness comment block.
- **Suggested revision**: Address the concern above.

