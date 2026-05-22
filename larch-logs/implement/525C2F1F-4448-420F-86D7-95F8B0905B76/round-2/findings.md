### FINDING_1: correctness: skills/implement/scripts/oos-disposition-shared.inc.bash:20-45
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Rejected-marker counter documents Rejected / Out-of-Scope headings but awk only extracts after ## Rejected A body that uses only a Rejected / Out-of-Scope heading (no ## Rejected line) records as rejected in the case filter yet yields zero counted markers; gate and oos-silent-drop scan can false-fail disposition Align awk capture with the documented heading shapes or narrow the jq/case filter to match implemented parsing only
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: skills/implement/scripts/oos-non-security-block-count.awk:12-16
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Security focus-area detection requires security plus specific delimiters Focus-area values like security-hardening are counted as non-security; disposition gate may stall runs that correctly tagged security-ish labels Document exact allowed tokens or broaden the prefix/boundary rule deliberately
- **Suggested revision**: Address the concern above.

### FINDING_3: risk-integration: skills/implement/SKILL.md:3298-3304
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Gate omits --oos-issues-ndjson when session-id file is empty If session-id is missing but accepted OOS exists and URLs exist only in the NDJSON batch, filed URL and rejection evidence are skipped; gate may exit 1 incorrectly Always pass the NDJSON path when known or exit 2 when required evidence paths cannot be resolved
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/implement/scripts/oos-disposition-gate.sh:55-58;skills/implement/scripts/oos-disposition-gate.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Inline-triage match is substring Inline-triage rule not rule N: Unrelated commit messages containing the substring can satisfy inline >= non_security without real per-OOS triage breadcrumbs Tighten grep pattern to the planned Inline-triage rule N: shape if false positives matter
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: (plan vs branch)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan file list omits shared inc and awk helpers None for runtime; traceability only Update planning template or commit message to mention shared helpers when present
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: larch-logs/implement/CDC300EE-EE59-4E8B-8ED8-5F6CA6D2571E/plan-goals-test.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Archived plan-goals text reflects pre-fix CALLER_KIND drift narrative Human audit of that run may misread state vs merged ship-pr/test fixes Optional log editorial cleanup only; not shipped runtime surface
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:88-115
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] oos-silent-drop inline-triage probe uses live repo HEAD merge-base, not run-log git identity Auditing a copied RUN_DIR from another cwd/branch counts Inline-triage lines from the wrong git history → high-severity scan false pass or false fail. Derive range from run-log artifacts when available; document cwd coupling or refuse git path without manifest proof.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/implement/scripts/oos-non-security-block-count.awk:12-13
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Security-routed detection is case- and suffix-sensitive -focus-area: Security- or -security-related- is counted as non-security → false gate failure or wrong obligation set. Case-fold value; widen security prefix rule and add harness cases for capitalized / compound values.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/implement/SKILL.md:1787-1792
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Gate snippet omits --oos-issues-ndjson when session-id empty Disposition only in NDJSON but session-id missing → gate ignores NDJSON URLs/reject markers and exits 1. Fallback path/glob to staged oos-issues.ndjson without relying solely on RUN_ID.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] risk-integration: scripts/ship-pr.md:44-72
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Exit 5 doc lists CALLER_KIND generically, not both step8 tokens Operators cross-reading ship-pr.md vs updated ship-pr.sh may miss the same-version caller-kind token. Update ship-pr.md in a doc-only follow-up (file untouched by this diff).
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: .claude/skills/audit-runs/scripts/audit-scan-run.md:29-49
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New oos-silent-drop scan lacks contract doc update and test-audit-runs coverage per Edit-in-sync. Operators and future refactors rely on audit-scan-run.md and test-audit-runs for scan registry truth; drift risks silent removal of the scan case or wrong NDJSON expectations without CI signal. Add test-audit-runs fixtures for oos-silent-drop pass/skip/fail and refresh audit-scan-run.md Scans implemented list plus brief NDJSON field notes.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Regression harness never asserts filed URLs sourced only from --oos-issues-ndjson. A regression in the union path could ship while CHANGELOG claims NDJSON URLs satisfy disposition; CI would still pass on existing cases only. Add a passing harness where filed URLs exist only in the NDJSON sidecar.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: skills/implement/scripts/oos-disposition-shared.inc.bash:25-51
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] count_rejected_oos_markers_from_ndjson sums per-JSON-line counts without deduping OOS indices. Duplicate NDJSON rows repeating the same rejected OOS block inflate rejected_oos_markers and can mask a silent drop on another block. Dedup by OOS index or document writer uniqueness; optionally clamp rejected count when comparing to non_security_oos.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/test-implement-structure.sh:261-265
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] NEVER rule 18 string is not pinned despite plan text. A wording-only regression on the OOS_PENDING clearing rule could slip past structure tests. Add grep pin for the NEVER #18 distinctive substring.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] architecture: scripts/test-ship-pr.sh (branch)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Orthogonal CALLER_KIND token rename bundled with OOS feature branch. Increases diff surface for reviewers but ship-pr harness was updated in the same branch. No change required for OOS scope; keep merged PR description noting both themes if splitting later.
- **Suggested revision**: Address the concern above.

### FINDING_16: security: skills/implement/SKILL.md:1787-1792
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] _RUN_ID from session-id is interpolated into the oos-issues.ndjson path without normalization. Path segments like ../ can escape the intended larch-logs/implement/<id>/ directory so the gate reads the wrong NDJSON or arbitrary operator-readable files, weakening disposition enforcement. Validate _RUN_ID against a safe charset or canonicalize and assert path prefix under IMPLEMENT_TMPDIR/larch-logs/implement/.
- **Suggested revision**: Address the concern above.

### FINDING_17: security: .claude/skills/audit-runs/scripts/audit-scan-run.sh:486-493
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] New scan_oos_silent_drop uses find + awk on discovered paths without excluding symlinks. A tarball or log tree with an oos-accepted*.md symlink pointing outside RUN_DIR makes awk read out-of-tree content and distorts scan results. Use find -type f (and/or reject symlinks) before awk.
- **Suggested revision**: Address the concern above.

### FINDING_18: security: skills/implement/scripts/oos-disposition-shared.inc.bash:32-49
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] jq extracts full .body for each NDJSON line with no size bound. Extremely large body fields can exhaust memory/CPU during audit or gate runs on hostile logs. Cap line/body size or fail closed for oversize records.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: SECURITY.md
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] AGENTS.md expects SECURITY.md updates for security-relevant behavior; this branch changes OOS disposition and audit mechanics but does not touch SECURITY.md. Downstream consumers lack a documented trust boundary for the new gate and fork/repo-unavailable carve-outs. Add a concise SECURITY.md note covering OOS disposition gate and audit scan assumptions.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] architecture: .claude/skills/audit-runs/scripts/audit-scan-run.sh:54-59
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] eval-based required-arg check remains in a file touched by the branch. Not introduced or amplified by this diff; unchanged structural pattern. Refactor separately if eliminating eval is desired.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: skills/implement/SKILL.md:1787-1800
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Gate omits --oos-issues-ndjson when session-id yields empty _RUN_ID so NDJSON URL/rejection evidence is ignored. NEVER #18 requires the staged batch in the union; if disposition evidence lives only in oos-issues.ndjson the gate can exit 0 and OOS_PENDING clears while policy evidence was never counted. Resolve RUN_ID the same way log writers do; always pass --oos-issues-ndjson when the file exists; fail closed if OOS work is pending and the batch path cannot be resolved.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:486-516
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Recursive find sums all oos-accepted*.md which can double-count duplicate OOS markdown across review rounds versus the gate’s three-file aggregate. Multi-round run dirs inflate acc_total vs a single filed URL batch producing false fail (or distorted counts) on oos-silent-drop. Align scan inputs with the gate’s canonical accepted-OOS paths or dedupe blocks before totals.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: .claude/skills/audit-runs/scripts/audit-scan-run.sh:88-106
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Live git log merge-base..HEAD uses the auditor’s current checkout not the archived run’s branch. Unrelated local commits with Inline-triage strings can make a retroactive audit pass despite the original PR lacking those breadcrumbs. Prefer run-log artifacts or recorded SHAs for inline evidence; avoid unrelated HEAD history.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: skills/implement/scripts/oos-disposition-shared.inc.bash:32-48
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] jq failures skip NDJSON lines via continue undercounting rejected markers. Corrupted partial JSONL yields rejected=0 and can force gate exit 1 or skew audit results without surfacing parse failure. Surface jq errors (exit 2 or explicit error field) instead of silent continue.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: skills/implement/scripts/oos-non-security-block-count.awk:6-14
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Security focus-area match is case-sensitive on security prefix. Security-routed OOS written as Security is miscounted as non-security inflating obligations. Use case-insensitive prefix match for the focus-area value.
- **Suggested revision**: Address the concern above.

### FINDING_26: code-quality: skills/implement/SKILL.md:66-68
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] NEVER #18 prose uses repo_unavailable=true wording vs REPO_UNAVAILABLE state key. Operators may grep the wrong symbol and misconfigure carve-outs. Align prose with exact ship-pr-state.sh key name REPO_UNAVAILABLE.
- **Suggested revision**: Address the concern above.

### FINDING_27: architecture: scripts/ship-pr.sh:764-3007;scripts/test-ship-pr.sh:849-3126;scripts/test-ship-pr.md:3075-3077;skills/implement/SKILL.md;CHANGELOG.md;Makefile;.claude-plugin/plugin.json
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Branch includes #2539 caller_kind alignment version bump changelog Makefile and larch-logs flush not listed in OOS Implementation Plan Files to modify A reviewer tracing only the seven plan bullets cannot explain the full merge-base..HEAD diff or commit da47ae7f as part of the OOS scope Split unrelated work into its own PR or expand the written plan to enumerate those paths/commits
- **Suggested revision**: Address the concern above.

