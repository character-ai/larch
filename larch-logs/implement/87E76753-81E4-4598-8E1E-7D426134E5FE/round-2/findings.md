### FINDING_1: correctness: skills/review/scripts/aggregate-findings.sh (aggregate-validate.py revision_traceable_in_blocks)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Six-word prefix fallback matches against full scoped input corpus. Paraphrased or partly hallucinated revision text can pass traceability when its first six words appear in Concern or other non-revision prose, weakening the anti-paraphrase advisory. Remove prefix fallback or restrict fallback to input lines that actually carry fix directions; prefer full normalized substring only except for very short revisions.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/review/scripts/aggregate-findings.sh (aggregate-validate.py check_revision_traceability)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Legacy singular Suggested revision ignored when bullets also present. Inconsistent merged output could carry an untraced legacy line alongside traced bullets with no warning. Trace both forms or warn when both appear; optionally fail under strict mode.
- **Suggested revision**: Address the concern above.

### FINDING_3: risk-integration: Branch diff vs main (multiple top-level areas)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Independent change sets bundled in one diff. Higher review/rollback/cherry-pick cost; harder to attribute regressions to the voting-protocol slice alone. Split future PRs by theme or document explicit per-issue mapping in the PR body.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: skills/shared/reviewer-templates.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Template file not updated alongside new voting semantics in other surfaces. Only matters if repo policy requires template sync for this class of wording change. Confirm generation/sync policy separately; update templates if required by project convention.
- **Suggested revision**: Address the concern above.

### FINDING_5: correctness: skills/review/scripts/aggregate-findings.sh:390-433
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Dual-format merged blocks skip traceability for legacy singular Suggested revision when From bullets exist. A merged FINDING could carry both multi-reviewer bullets and a legacy singular line; only bullets are checked so a fabricated singular revision would not emit stderr warnings. Validate singular revision whenever present, or reject dual-format output in structural validation.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: skills/review/scripts/aggregate-findings.sh:302-334
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Suggested revisions sub-list parser terminates on any line matching ^-\\s*\\*\\*[A-Z]. A rare verbatim continuation formatted as a top-level - **Capital... line could truncate bullets and produce false warnings or missed traces. Restrict termination to known field headers or require indented continuation lines only.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/review-and-fix/scripts/review-and-fix.sh:5599-5602
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] compose_coder_prompt reframed from suggested-revision-driven to concern-first beyond the plan’s additive sentence. Accepted findings with thin Concern lines but precise suggested revisions might yield a coder who under-implements relative to reviewer intent. Re-add explicit primacy of suggested revision(s) alongside the new coder-decides language.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/review/scripts/aggregate-findings.sh:371-387
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Six-word prefix fallback loosens verbatim trace semantics. Prefix match can pass when full normalized revision text is absent from input corpus. Treat prefix-only hits as separate advisory or require full substring match by default.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:4590-4594
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] pr-create resume path no longer clears OOS_PENDING before advance; unrelated to voting protocol change. Behavior change may affect OOS resume semantics; not part of the vote-on-problems plan files. Review in context of #2551 / implement OOS gate work.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] architecture: Multiple paths (Makefile lint-bash32 audit-runs CHANGELOG plugin.json larch-logs)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Branch bundles non-review-protocol changes and run logs. Noise for reviewers targeting only voting semantics; logs are policy-allowed. Treat as separate review slices or split PRs.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-dispatch-code-voters.sh:182-186
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] New voter NO-guidance line in dispatch-code-voters.sh is not asserted by the harness. Wording-only regression or accidental deletion of the anti-NO-on-fix-copy instruction could ship without test failure. Add grep -Fq for a distinctive substring from the new printf line alongside existing *-vote-prompt.txt checks in the happy-path loop.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: .claude/skills/audit-runs/scripts/audit-scan-run.sh:89-124
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] When neither codex-commit-message nor session-transcript exists under RUN_DIR the scan counts Inline-triage via the current repo git log range. Auditing a copied or partial run directory without those artifacts can attribute unrelated local commit messages to that run and skew oos-silent-drop pass/fail. When no run-local artifacts exist return zero or mark scan incomplete unless caller supplies an explicit repo+revision range; do not default to ambient HEAD history.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/implement/scripts/oos-disposition-shared.inc.bash:35-40
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] jq parse failures on oos-issues.ndjson lines are skipped with only a stderr line. Partially corrupted NDJSON can yield a rejected-marker count that omits some rejection sections while still appearing mechanically computed. Count jq failures and fail closed (or structured incomplete) when any line fails to parse in gate-critical mode.
- **Suggested revision**: Address the concern above.

### FINDING_14: security: skills/review-and-fix/scripts/review-and-fix.sh:213-221
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Coder prompt explicitly marks Justification as untrusted and limits scope of suggested revisions. Reduces risk of reviewer prose being executed as imperative instructions by the coder agent. No change required; mirror in any duplicate coder prompt paths if they exist.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: .claude/skills/audit-runs/scripts/audit-scan-run.sh:197-232;.claude/skills/audit-runs/scans.tsv
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New oos-silent-drop scan without matching audit-scan-run.md and test-audit-runs updates. Registry/docs/tests can drift; scan could be removed or reshaped without CI catching wrong NDJSON contracts. Add test-audit-runs fixtures for pass/skip/fail and refresh audit-scan-run.md scan list and NDJSON field notes alongside the implementation.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: skills/implement/scripts/oos-disposition-shared.inc.bash:32-48
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] jq parse errors skip NDJSON lines when counting rejected OOS markers. Corrupted JSONL undercounts rejections; gate or audit can false-fail disposition or mislead operators. Fail closed on jq errors or count parse failures separately and surface as exit 2 / explicit scan error.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: skills/review/scripts/aggregate-findings.sh:371-387
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Single-word suggested revisions never pass the six-word prefix fallback in revision_traceable_in_blocks. Spurious advisory warnings; strict env can fail validation on otherwise faithful one-word quotes. Add single-token matching or document exempt short revisions.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/test-implement-structure.sh:241-265
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] NEVER #18 gate-before-clear rule lacks a grep pin unlike adjacent OOS invariants. Wording-only regressions on NEVER #18 could ship without structure harness signal. Pin a distinctive NEVER #18 substring tied to oos-disposition-gate.sh.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] risk-integration: scripts/ship-pr.md:41-44
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Generic Exit-5 CALLER_KIND documentation vs concrete ship-pr.sh tokens. Cross-read confusion for operators; not introduced by this branch’s touched files. Doc-only follow-up aligning ship-pr.md with ship-pr.sh tokens.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/review-and-fix/scripts/review-and-fix.sh:221
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] compose_coder_prompt rewrote the primary fix directive (Concern-first, new Justification rules) instead of only appending the planned coder sentence after the Suggested revision reference. Coders may prioritize Concern over the verbatim multi-reviewer revision list the plan was designed to preserve for implementation, diverging from the stated “add a sentence” change. Restore the original suggested-revision-centric directive and append only the plan’s sentence (plus minimal plural/legacy wording if needed).
- **Suggested revision**: Address the concern above.

### FINDING_21: architecture: diff vs merge-base(main)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Branch bundles many changes and commits outside the five-file implementation plan (e.g. ship-pr OOS gate #2540, lint-bash32 *.inc.bash, version bump, implement SKILL/harness updates, full larch-logs run directory). Plan-to-PR traceability is weakened: reviewers cannot tell which requirements govern the extra files. Split PRs or expand the written plan to cover every intentional surface in the diff.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/review/scripts/aggregate-findings.sh:357-418
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Revision traceability uses reviewer-intersection scoping and a six-word prefix fallback, not only the plan’s substring-over-input-for-slot rule. Warnings or passes can differ from the plan’s literal matching rule; strict mode behavior depends on undocumented heuristics. Match the plan’s corpus definition or document and approve the stricter heuristic as the new contract.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: scripts/dispatch-code-voters.sh:63
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Voter prompt omits “or distrust” compared to the plan’s quoted sentence. Slight mismatch to the agreed voter copy; unlikely to break behavior but fails literal plan fidelity. Insert “or distrust” to mirror the plan text.
- **Suggested revision**: Address the concern above.

