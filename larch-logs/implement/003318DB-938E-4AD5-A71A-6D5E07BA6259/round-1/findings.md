### FINDING_1: **Important** correctness — `scripts/dispatch-code-voters.sh:240`: stale `*-first-pass.txt` sidecars are never removed when a later run in the same `REVIEW_TMPDIR` takes the no-retry or retry-fail path. `review-and-fix.sh` can rerun `review-core.sh` against the same `round-$N` directory during degraded-panel retry; if the first run wrote `codex-vote-output-first-pass.txt` and the retry run parses cleanly, line 241 returns `OK` and the old sidecar remains, so `larch-log.sh write-round` commits stale first-pass content for the current round. Compute the first-pass sidecar path at the start of `check_and_retry_voter_parse_rate` and `rm -f` it before the initial parse-rate check, then reuse that path on retry success; add a regression that precreates a sidecar and verifies clean/no-retry and retry-fail runs remove it.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** correctness — `scripts/dispatch-code-voters.sh:240`: stale `*-first-pass.txt` sidecars are never removed when a later run in the same `REVIEW_TMPDIR` takes the no-retry or retry-fail path. `review-and-fix.sh` can rerun `review-core.sh` against the same `round-$N` directory during degraded-panel retry; if the first run wrote `codex-vote-output-first-pass.txt` and the retry run parses cleanly, line 241 returns `OK` and the old sidecar remains, so `larch-log.sh write-round` commits stale first-pass content for the current round. Compute the first-pass sidecar path at the start of `check_and_retry_voter_parse_rate` and `rm -f` it before the initial parse-rate check, then reuse that path on retry success; add a regression that precreates a sidecar and verifies clean/no-retry and retry-fail runs remove it.
- **Suggested revision**: Address the concern above.

### FINDING_2: **[correctness]** [`scripts/dispatch-code-voters.sh:263-265`](scripts/dispatch-code-voters.sh:263-265) — After a best-effort `cp "$voter_path" "$first_pass_sidecar" 2>/dev/null || true`, `emit_breadcrumb` always says first-pass content was preserved even when `cp` failed (disk full, permissions, etc.), so operators can be misled into thinking the sidecar exists and matches the pre-retry file. **Suggested fix:** Only emit that breadcrumb when `cp` succeeds (e.g. run `cp` in an `if cp ...; then ... emit_breadcrumb ...; fi` or test `-f "$first_pass_sidecar"` and compare size/sha after copy), or reword the message to “attempted to preserve … (best-effort)” when not verifying success.
- **Reviewer**: dyn-observability-sidecar-output.txt
- **Concern**: - **[correctness]** [`scripts/dispatch-code-voters.sh:263-265`](scripts/dispatch-code-voters.sh:263-265) — After a best-effort `cp "$voter_path" "$first_pass_sidecar" 2>/dev/null || true`, `emit_breadcrumb` always says first-pass content was preserved even when `cp` failed (disk full, permissions, etc.), so operators can be misled into thinking the sidecar exists and matches the pre-retry file. **Suggested fix:** Only emit that breadcrumb when `cp` succeeds (e.g. run `cp` in an `if cp ...; then ... emit_breadcrumb ...; fi` or test `-f "$first_pass_sidecar"` and compare size/sha after copy), or reword the message to “attempted to preserve … (best-effort)” when not verifying success.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] **[correctness]** [`scripts/dispatch-code-voters.sh:258-266`](scripts/dispatch-code-voters.sh:258-266) — Ordering (`cp` then `mv`) and path handling (`*.txt` → `…-first-pass.txt`, else `…-first-pass`) match the intended invariant; retry-fail path has no `cp` and leaves `voter_path` unchanged, consistent with the plan. No separate finding beyond the unconditional breadcrumb-vs-`cp` mismatch above.
- **Reviewer**: dyn-observability-sidecar-output.txt
- **Concern**: - **[correctness]** [`scripts/dispatch-code-voters.sh:258-266`](scripts/dispatch-code-voters.sh:258-266) — Ordering (`cp` then `mv`) and path handling (`*.txt` → `…-first-pass.txt`, else `…-first-pass`) match the intended invariant; retry-fail path has no `cp` and leaves `voter_path` unchanged, consistent with the plan. No separate finding beyond the unconditional breadcrumb-vs-`cp` mismatch above.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] **[correctness]** [`scripts/lib-quiet.sh:114-119`](scripts/lib-quiet.sh:114-119) — `emit_breadcrumb` uses plain `printf` to stdout when `LARCH_QUIET_BREADCRUMBS` is unset; in a normal `larch_quiet_init` process that is the quiet log, but inside `$(check_and_retry_voter_parse_rate …)` stdout is the command-substitution capture pipe, so breadcrumbs would pollute `VOTER_*_PARSE_RATE_STATUS` without a redirect. This branch’s `{ … } >&2` in [`scripts/dispatch-code-voters.sh:264-265`](scripts/dispatch-code-voters.sh:264-265) correctly addresses that interaction; the subtlety is pre-existing library behavior, not a defect in the new sidecar logic.
- **Reviewer**: dyn-observability-sidecar-output.txt
- **Concern**: - **[correctness]** [`scripts/lib-quiet.sh:114-119`](scripts/lib-quiet.sh:114-119) — `emit_breadcrumb` uses plain `printf` to stdout when `LARCH_QUIET_BREADCRUMBS` is unset; in a normal `larch_quiet_init` process that is the quiet log, but inside `$(check_and_retry_voter_parse_rate …)` stdout is the command-substitution capture pipe, so breadcrumbs would pollute `VOTER_*_PARSE_RATE_STATUS` without a redirect. This branch’s `{ … } >&2` in [`scripts/dispatch-code-voters.sh:264-265`](scripts/dispatch-code-voters.sh:264-265) correctly addresses that interaction; the subtlety is pre-existing library behavior, not a defect in the new sidecar logic.
- **Suggested revision**: Address the concern above.

### FINDING_5: architecture: scripts/dispatch-code-voters.sh:259-261 vs scripts/larch-log.sh:266
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Non-.txt voter_path branch produces a sidecar name not covered by *-vote-output-first-pass.txt documentation or tests. Hypothetical non-.txt voter_path without -output- in basename: sidecar may not pass round_artifact_included. Extend allow-list and docs for the extension suffix, or remove the dead branch if contract is .txt-only.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/larch-log.sh:266
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Explicit allow-list glob duplicates broader *-output-*.txt matching for canonical first-pass names. No runtime breakage; minor maintenance noise if patterns drift. Optional comment instead of duplicate glob, or keep as-is for documentation value.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/dispatch-code-voters.md:46
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Change 5 doc describes first-pass sidecar and best-effort copy but omits the planned success-path emit_breadcrumb discoverability signal Operators reading only dispatch-code-voters.md may not know a breadcrumb announces the sidecar basename after a successful parse-retry Extend the parse-retry paragraph to mention the success-path breadcrumb (and stderr if worth documenting)
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/dispatch-code-voters.sh:257-265 scripts/larch-log.sh:266-267
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Non-.txt voter_path writes extensionless first_pass_sidecar but round_artifact_included only allow-lists *-vote-output-first-pass.txt If a future non-.txt canonical voter path ever uses parse-retry success the sidecar is written on disk but write-round will not commit it so first-pass content stays out of run logs Add allow-list pattern for the extensionless sidecar or remove/document the *) branch as unsupported
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/dispatch-code-voters.sh:263-265
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Breadcrumb claims first-pass was preserved after best-effort cp that ignores failures. Disk full or permission error: cp fails, mv still promotes retry; operators see a preserved-at message but no sidecar file, undermining observability and trust in breadcrumbs. Emit preserved message only after verifying the sidecar exists (and optionally matches source), or emit a different message when cp fails.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/dispatch-code-voters.sh:263
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] cp stderr discarded and failures swallowed with no substitute signal. ENOSPC on tmpdir: silent loss of sidecar with no stderr hint beyond optional misleading breadcrumb. Log cp failures to stderr without failing the retry, or tie messaging to cp success.
- **Suggested revision**: Address the concern above.

### FINDING_11: security: scripts/dispatch-code-voters.sh:258-265;scripts/larch-log.sh:92-120
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Parse-retry success now copies the full first-pass voter file to a sidecar before promotion; write-round stages allowed *.txt artifacts through larch_log_redact_file. Committed round logs can retain the complete discarded narrative; that text can be noisier than promoted structured votes, so redaction gaps or operator misuse of published logs slightly increase the chance of retaining incidental secrets or sensitive wording versus the pre-change behavior where the narrative was not kept at a stable path for logging. Add redaction regression fixtures for representative *-vote-output-first-pass.txt content and document the artifact as high-sensitivity in run-log or security operator guidance.
- **Suggested revision**: Address the concern above.

