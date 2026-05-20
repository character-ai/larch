### FINDING_1: **Important** correctness [scripts/scout-dynamic-archetypes.sh:267](<OPERATOR_REPO_PATH>/scripts/scout-dynamic-archetypes.sh:267) — The new fence-stripping path can make the scout exit nonzero before it reaches the `json_parse` failure emitter. Concrete scenario: a launcher exits `0` but fails to create `$raw_output`; line 262 enters the recovery branch because `jq` cannot read it, then line 267 runs `awk` on the missing file under `set -e`, aborting the script. `dispatch-panel.sh:313-315` then reports `SCOUT_STATUS=validation-failed`, so there is no `SCOUT_FAIL_REASON=json_parse` and no parse-failure execution-issues warning. Guard the `awk` extraction with a readable-file check or tolerate `awk` failure, then let the existing `jq` gate at lines 275-277 emit the normal `json_parse` result.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** correctness [scripts/scout-dynamic-archetypes.sh:267](<OPERATOR_REPO_PATH>/scripts/scout-dynamic-archetypes.sh:267) — The new fence-stripping path can make the scout exit nonzero before it reaches the `json_parse` failure emitter. Concrete scenario: a launcher exits `0` but fails to create `$raw_output`; line 262 enters the recovery branch because `jq` cannot read it, then line 267 runs `awk` on the missing file under `set -e`, aborting the script. `dispatch-panel.sh:313-315` then reports `SCOUT_STATUS=validation-failed`, so there is no `SCOUT_FAIL_REASON=json_parse` and no parse-failure execution-issues warning. Guard the `awk` extraction with a readable-file check or tolerate `awk` failure, then let the existing `jq` gate at lines 275-277 emit the normal `json_parse` result.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: larch-logs/implement/284806AD-D433-4D0C-AED3-6B7D11740C78/
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Chore implement run-log directory appears in branch diff. Excluded by reviewer scope rules for larch-logs flush commits. No action for plan fidelity.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] correctness: Plan verification Makefile targets
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Cannot confirm make targets were run from diff-only review. Not a code defect; only unverified process evidence. Run the listed targets in CI or locally before merge.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] correctness: skills/review/scripts/dispatch-panel.sh:337-345
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Cached ok status + invalid manifest updates memory but may not rewrite scout-roundN-status.env. Stale sidecar says ok while live state is parse-failed until another component overwrites the file. Call write_scout_status_file after mutating SCOUT_STATUS in the cached branch (pre-existing gap).
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: scripts/append-execution-issue.sh:58-62
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] LARCH_EXECUTION_ISSUES_LOG selects an arbitrary filesystem target for append. Operator-controlled env can direct writes outside intended dirs if permissions allow. Document trust model; optionally validate log path prefix against session tmp roots.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] security: skills/review/scripts/dispatch-panel.sh:320-324
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] SCOUT_OUTPUT from scout stdout is assigned into SCOUT_MANIFEST; a hostile scout binary could point at an unexpected path. Pre-existing wiring; not introduced by this branch. Harden by ignoring SCOUT_OUTPUT when manifest path is already known, or validate path against REVIEW_TMPDIR.
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: skills/review/SKILL.md; skills/review/references/heavy-worker.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan file list omitted these updates but branch changes them for SCOUT_FAIL_REASON KV handling. Orchestration docs drift from the written seven-file plan checklist only; behavior is aligned with the feature. Update the implementation plan template or accept as intentional ancillary doc sync.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/scout-dynamic-archetypes.sh:263-265
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] SCOUT_FAIL_REASON=fence_strip_io is emitted on mktemp failure, which is not fence-specific. Operators mis-attribute temp-file failures as fence-strip I/O in SCOUT_FAIL_REASON aggregates. Rename token or emit a distinct reason for mktemp failures.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/test-scout-dynamic-archetypes.sh:30-38
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] jq test stub keys only argv positions -c and --argjson Reordering scout's jq invocation can silently stop covering validation_jq_error Stub on full argv/env sentinel instead of fixed positional args
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: skills/review/scripts/dispatch-panel.sh:255-265 and skills/review/scripts/review-core.sh:96-105
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated execution-issues log path resolution vs existing review-core helper Two maintenance surfaces can diverge when the execution-issues path contract changes Extract or source one canonical resolver used by dispatch-panel and review-core
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/scout-dynamic-archetypes.sh:262-272
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Fence stripper concatenates multiple fenced regions Multiple ``` blocks can merge into invalid JSON and surface as json_parse instead of a clearer failure Pick first jq-valid fenced block or strip a single best block
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/scout-dynamic-archetypes.sh:262-276
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Fence-strip path runs under set -e; awk/mv failure exits non-zero so dispatch maps scout to validation-failed instead of parse-failed/SCOUT_FAIL_REASON. Disk full or permission error during mv after successful fenced JSON extraction: scout exits before emit_parse_failed_result; dispatch shows validation-failed and loses telemetry semantics. Wrap fence extraction in set +e (or explicit || true) and convert I/O failures into emit_parse_failed_result with a dedicated reason without non-zero exit.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/scout-dynamic-archetypes.sh; scripts/scout-dynamic-archetypes.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan Part C enumerated three scout-local SCOUT_FAIL_REASON tokens; implementation adds invalid_archetypes_shape and fence_strip_io plus tests/docs. Readers comparing only the plan bullets might think telemetry is incomplete when it is not. Amend planning docs to list the full token enum or treat as acceptable plan underspecification.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: skills/review/scripts/dispatch-panel.sh:337-345;skills/review/scripts/test-dispatch-panel.sh:294-312
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Reused status sidecar can carry SCOUT_STATUS=parse-failed without SCOUT_FAIL_REASON; stdout omits the key and execution-issues use reason=unknown. reuse-empty-with-status fixture: parse-failed with no fail-reason line for downstream parsers expecting SCOUT_FAIL_REASON whenever SCOUT_STATUS=parse-failed. Default SCOUT_FAIL_REASON when sidecar says parse-failed but the key is missing (e.g. cached_parse_failed).
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/scout-dynamic-archetypes.sh:262-276
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Fence strip concatenates all fenced regions Multiple markdown code blocks can concatenate into invalid or wrong JSON reintroducing parse-failed in production Add multi-block regression test or change extraction to select the valid JSON block e.g last fenced segment or first jq-valid slice
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/review/scripts/dispatch-panel.sh:267-269
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] append_scout_parse_issue returns early when append-execution-issue.sh is not executable (-x check). Parse-failed rounds in a broken-permission checkout would skip the execution-issues warning without WARN fallback from this guard. Use -f test plus invoke and rely on exit code WARN path, or emit WARN when helper exists but is not executable.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/review/scripts/dispatch-panel.sh:268-269
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] -x guard skips append helper with no WARN Some environments may lose +x on the helper; warnings never reach execution-issues Use -f plus explicit bash or WARN when helper is present but not executable
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/review/scripts/emit-tally.sh:127-135 skills/review/scripts/emit-tally.md:5 skills/review/scripts/test-review-core.sh:190-191
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] SCOUT_FAIL_REASON not in review-summary.json emit path Downstream consumers that only read review-summary.json never see scout parse failure reasons despite new telemetry elsewhere Add optional --scout-fail-reason to emit-tally.sh panel jq object update emit-tally.md and jq assertions in test-review-core.sh test-emit-tally.sh
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/review/scripts/test-dispatch-panel.sh:294-312
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Stale sidecar parse-failed without SCOUT_FAIL_REASON untested SCOUT_FAIL_REASON omitted on stdout and execution log uses unknown without assertion drift could hide regressions Add grep for SCOUT_FAIL_REASON absence or expected unknown and optional execution-issues.md check under REVIEW_TMPDIR
- **Suggested revision**: Address the concern above.

### FINDING_20: security: skills/review/scripts/dispatch-panel.sh:272-289
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Unescaped SCOUT_FAIL_REASON and SCOUT_MANIFEST are interpolated into a double-quoted --entry argument when calling append-execution-issue.sh. Bash expands command substitutions inside the expanded string, so a crafted scout status sidecar (or other source) setting SCOUT_FAIL_REASON to e.g. $(malicious) can execute arbitrary commands during parse-failed handling. Pass the message via --entry-file from a tempfile, or sanitize/allowlist reason tokens, or build argv without double-quote expansion of untrusted substrings.
- **Suggested revision**: Address the concern above.

