### FINDING_14: risk-integration: scripts/test-implement-structure.sh:264-265
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Step 7a timing-ledger mark was removed from generate-code-flow-diagram.sh and is not in step-7a.sh but the structural harness still requires it in generate-code-flow-diagram.sh. make lint runs test-implement-structure in shard-14 and fails with generate-code-flow-diagram.sh must contain Step 7a timing-ledger mark blocking merge. Restore Step 7a token/timing marks in step-7a.sh and repoint test-implement-structure.sh to grep step-7a.sh instead of generate-code-flow-diagram.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_2: code-quality: scripts/test-implement-structure.sh:263-265
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Structural harness still pins Step 7a timing mark inside generate-code-flow-diagram.sh after marks moved out. make test-implement-structure fails on this branch while make test-step-7a can pass. Repoint grep to step-7a.sh (and token-ledger if desired) instead of generate-code-flow-diagram.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `skills/implement/scripts/step-7a.sh:105-106` — `ARCHITECTURE_DIAGRAM_FILE` is still read with only `-f` gating and `cat`, then published (after `redact-secrets.sh` in `tracking-issue-summary.sh`). A same-UID writer that poisons the env var could exfiltrate arbitrary local file bytes into a tracking-issue comment. This matches pre-main SKILL.md Step 7a; the diff moves logic, not the gate. **Suggested fix:** confine reads to the session/design tmpdir (canonical path under `$IMPLEMENT_TMPDIR` or manifest) and run `sanitize-mermaid-fragment.sh` on architecture content before upsert, matching `ship-pr.sh`’s PR-body path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_25: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `skills/implement/scripts/step-7a.sh:295-300` — `LARCH_CLAUDE_PLUGIN_ROOT` from `session-env.sh` can repoint `$PLUGIN_ROOT` to an alternate tree before sourcing helpers. Same trust model as other `/implement` rehydration preludes (session artifacts are operator-account data, not a hostile-UID boundary). **Suggested fix:** only accept plugin roots under the known install path or validate against `realpath` + allowlist before `source`/exec.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_26: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **architecture** `skills/implement/references/pr-body-template.md:21-27` vs `step-7a.sh:103-116` — PR creation sanitizes diagram files; `larch:diagrams` composition does not re-sanitize architecture (and never did on main). Pre-existing inconsistency, not introduced by this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_38: [OUT_OF_SCOPE] architecture: skills/implement/scripts/step-7a.sh:404-405
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] REBASE_OUTCOME failure path emits tail without LOG_FLUSH_STATUS. KV consumers may see empty LOG_FLUSH_STATUS when flush was intentionally skipped. Document or set explicit skipped-rebase LOG_FLUSH_STATUS on early exit.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_41: [OUT_OF_SCOPE] **`set -e` at `skills/implement/scripts/step-7a.sh:401`:** It is re-enabled only for `cat "$rebase_out"` and the `rebase_rc` gate; `run_log_flush` immediately executes `set +e` at `skills/implement/scripts/step-7a.sh:144`, so flush helpers are not running under errexit. The duplicate `set +e` pairs in `run_larch_log_write` (`skills/implement/scripts/step-7a.sh:122-130`) are redundant, not harmful. Residual risk is only `cat` failing before `emit_tail` on the success path (missing capture file).
- **Reviewer**: dyn-bash-fd-propagation-output.txt
- **Concern**: - **`set -e` at `skills/implement/scripts/step-7a.sh:401`:** It is re-enabled only for `cat "$rebase_out"` and the `rebase_rc` gate; `run_log_flush` immediately executes `set +e` at `skills/implement/scripts/step-7a.sh:144`, so flush helpers are not running under errexit. The duplicate `set +e` pairs in `run_larch_log_write` (`skills/implement/scripts/step-7a.sh:122-130`) are redundant, not harmful. Residual risk is only `cat` failing before `emit_tail` on the success path (missing capture file).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_42: [OUT_OF_SCOPE] **`capture-session-transcript.sh` rc handling (`skills/implement/scripts/step-7a.sh:186-191`):** That helper always `exit 0` (`scripts/capture-session-transcript.sh`), so the `LOG_FLUSH_STATUS=degraded` branch for non-zero rc is unreachable; behavior matches pre-consolidation SKILL semantics (status via execution-issues append + post-transcript flush).
- **Reviewer**: dyn-bash-fd-propagation-output.txt
- **Concern**: - **`capture-session-transcript.sh` rc handling (`skills/implement/scripts/step-7a.sh:186-191`):** That helper always `exit 0` (`scripts/capture-session-transcript.sh`), so the `LOG_FLUSH_STATUS=degraded` branch for non-zero rc is unreachable; behavior matches pre-consolidation SKILL semantics (status via execution-issues append + post-transcript flush).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_43: [OUT_OF_SCOPE] **Sanitizer upsert skip vs `main`:** Skipping `larch:diagrams` upsert on `STATUS=skipped` / sanitizer-shaped `SKIP_REASON` is an intentional plan change, not a byte-identical carryover from `main` (which always upserted when `ISSUE_NUMBER` was set).
- **Reviewer**: dyn-bash-fd-propagation-output.txt
- **Concern**: - **Sanitizer upsert skip vs `main`:** Skipping `larch:diagrams` upsert on `STATUS=skipped` / sanitizer-shaped `SKIP_REASON` is an intentional plan change, not a byte-identical carryover from `main` (which always upserted when `ISSUE_NUMBER` was set).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_47: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-stub-model-accuracy-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:403-406` — On rebase probe non-zero exit, the helper `exit "$rebase_rc"` before `run_log_flush`, so pre-bump flush does not run on conflict. `test-step-7a.sh:437-444` encodes that behavior; it may be intentional for macro routing but diverges from plan text saying the helper exits 0 except argv errors.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_48: [OUT_OF_SCOPE] On `main`, `skills/implement/SKILL.md` always upserted `larch:diagrams` when `ISSUE_NUMBER` was set, including after sanitizer rejection (`STATUS=skipped` with a placeholder). This branch suppresses upsert for all `STATUS=skipped` outcomes; that matches the issue plan but conflicts with the stated “byte-identical `larch:diagrams`” acceptance criterion.
- **Reviewer**: dyn-stub-model-accuracy-output.txt
- **Concern**: - On `main`, `skills/implement/SKILL.md` always upserted `larch:diagrams` when `ISSUE_NUMBER` was set, including after sanitizer rejection (`STATUS=skipped` with a placeholder). This branch suppresses upsert for all `STATUS=skipped` outcomes; that matches the issue plan but conflicts with the stated “byte-identical `larch:diagrams`” acceptance criterion.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] architecture: skills/implement/scripts/step-7a.sh:367-369
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Broad SKIP_REASON glob may suppress upsert on non-sanitizer failures containing reject. Hypothetical helper-error text with reject substring skips larch:diagrams upsert incorrectly. Match explicit sanitizer REASON_TOKEN values from sanitize-mermaid-fragment.sh when editing this logic.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_9: correctness: scripts/test-implement-structure.sh:263-265
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Structure test still requires Step 7a timing mark in generate-code-flow-diagram.sh after marks were removed. make lint fails test-implement-structure on this branch. Restore marks in step-7a.sh and update the test pin, or update the assertion with documented intent.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

