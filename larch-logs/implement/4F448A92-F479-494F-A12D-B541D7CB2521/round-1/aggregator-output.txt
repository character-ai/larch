Here is the normalized structured finding list. Multiple inputs described the same risk and are merged; `[OUT_OF_SCOPE]` is preserved on merged headings where any source was tagged that way. Verbatim suggested revisions: slots that only said “Address the concern above.” are merged into one bullet when the wording is identical across those slots.

### FINDING_1: `scripts/ship-pr.md` omits `RELEVANT_CHECKS_SKIPPED` in helper success contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Prose in the sibling / Helper Contracts area still treats success as `RELEVANT_CHECKS_OK=true` only, while `ship-pr.sh` (e.g. `is_relevant_checks_clean`) treats `RELEVANT_CHECKS_SKIPPED=true` as a non-failing, clean outcome on rc=0. Readers, fork operators, or tests derived from the doc can encode OK-only predicates, stall, mis-handle skip, or miss stderr skip breadcrumbs relative to the implemented helper contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

### FINDING_2: `skills/review/references/domain-rules.md` genericity vs `scripts/` exemption conflict
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Genericity rules describe `scripts/` as generic and also as consumer-local exempt, so Step 3 reviewers may skip valid genericity findings for shared `scripts/` or mis-apply exemptions beyond true consumer-local helpers. Risk is inconsistent review application unless the exemption is scoped to explicit paths (named scripts vs blanket `scripts/`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

---

### FINDING_3: Unrelated `git checkout` fixture churn in `scripts/test-ship-pr.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Many prep helpers show `checkout -b` vs `checkout -B` (or similar) changes alongside relevant-checks / SKIPPED work, increasing review surface and risk of unintended harness behavior without a clear tie to the migration; bisect and attribution suffer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

### FINDING_4: `is_relevant_checks_clean` in `scripts/ship-pr.sh` is brittle to envelope grammar / line endings
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Matching requires a space after `=true` (and line-anchored, LF-split parsing). Future one-token success lines, missing trailing fields, missing the single trailing space, leading CR on the envelope line, or other stdout drift while rc stays 0 can make `is_relevant_checks_clean` false, triggering REDACTED_LOG_FILE parsing / `resolve_checks_log_path` paths and stalling or mis-handling nominally clean outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Relax the regex to allow optional whitespace or EOL after =true (and/or strip CR), and extend test-ship-pr fixtures to cover longest SITE labels and CRLF-prefixed capture.

---

### FINDING_5: [OUT_OF_SCOPE] `skills/review-and-fix/SKILL.md` validation line and SKIPPED symmetry
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: [OUT_OF_SCOPE] Validation references the captured helper only; SKIPPED semantics are not called out—optional editor clarity, not asserted as a regression from this branch; optional symmetry with SECURITY.md observability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

---

### FINDING_6: [OUT_OF_SCOPE] Extra `larch-logs/**` commits on branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: [OUT_OF_SCOPE] Noise in git history from run-log commits; expected by project policy unless auditing log content quality.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

---

### FINDING_7: Docs vs skill wording mismatch (fenced helper vs inline Step 3e)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `docs/linting.md` (and related harness doc) describe a fenced helper invocation for `/review` Step 3e while the skill uses inline prose, inviting churn or false belief that docs/harness disagree with runtime behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

---

### FINDING_8: `scripts/test-relevant-checks-helper-failure.sh` non-executable branch lacks `EXIT_CODE=126` stdout assertion
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The check-script-not-executable case does not assert `EXIT_CODE=126` on stdout, so a regression could drop `EXIT_CODE` from the envelope without failing the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

---

### FINDING_9: Dangling / broken `scripts/relevant-checks.sh` symlink classified as absent → `RELEVANT_CHECKS_SKIPPED` (exit 0)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: A symlink that exists but is broken can be treated like a missing script, emitting SKIPPED with exit 0, so broken consumer wiring can look like an intentional omit-skip and bypass local checks without a distinct failure/reason unless product chooses fail-closed or a dedicated reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Add explicit broken-symlink detection and a failure or dedicated reason plus a helper-failure harness assertion.

---

### FINDING_10: [OUT_OF_SCOPE] Historical `CHANGELOG.md` still names old `/relevant-checks` / deleted skill paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: [OUT_OF_SCOPE] Old changelog entries reference removed paths; reader confusion when browsing history; excluded from some acceptance greps; optional editorial cleanup separate from this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

---

### FINDING_11: [OUT_OF_SCOPE] Run log embeds plan slash-command text
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: [OUT_OF_SCOPE] Flushed run log content in `larch-logs/.../plan-goals-test.md`; negligible when using planned grep exclusions for `larch-logs`; only if repo policy changes on log hygiene.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

---

### FINDING_12: `skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh` does not pin `RELEVANT_CHECKS_SKIPPED=true`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Unlike the review harness, the implement anti-halt harness does not require `RELEVANT_CHECKS_SKIPPED=true` in the continuation window, so SKILL.md skip-continuation wording could regress without CI until a manual `/implement` mis-halts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---

### FINDING_13: Missing consumer `scripts/relevant-checks.sh` yields exit 0 + SKIPPED; automation may assume checks ran
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Absent script produces exit 0 and `RELEVANT_CHECKS_SKIPPED=true`; implement/review treat SKIPPED like OK so local pre-commit-scoped checks do not run; branches without the script can still progress while automation may treat rc=0 as “checks ran.” `ship-pr.sh` phases that use `is_relevant_checks_clean` can advance on skip the same way, completing checks phases without running consumer relevant-checks. Mitigations suggested include CI/branch policy, treating SKIPPED as non-green in automation, requiring the script where gates are mandatory, and optionally a strict mode that treats SKIPPED as failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Enforce CI/branch policy; treat RELEVANT_CHECKS_SKIPPED as non-green in automation; require the script where larch gates are mandatory.
  - From cursor-specialist-security-output.txt: Ship-pr can complete its checks phase without ever running consumer relevant-checks when the file is missing. Same as above for finalize automation; optionally add a strict mode that treats SKIPPED as failure.

---

### FINDING_14: [OUT_OF_SCOPE] Documented policy tradeoff: skip-on-missing-script vs fail-closed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: [OUT_OF_SCOPE] Explicit skip-on-missing-script (exit 0 + `RELEVANT_CHECKS_SKIPPED`) trades prior fail-closed missing-check behavior for observability-first continuation; consumer repos without the script can merge flows without local lint unless CI/backstop catches—documented policy, not an accidental parser bug; no code change unless product wants fail-closed again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---

### FINDING_15: `hooks/hooks.json` removed PreToolUse deny for Skill(relevant-checks) during active runs
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: [latent] With the skill removed, a fork that re-adds a `relevant-checks` skill no longer gets the old mechanical deny during active implement/review unless the hook is re-registered or fork policy is documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

---

### FINDING_16: `EXIT_CODE=126` + `FAILURE_REASON=check-script-not-executable` conflates non-invokable shapes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: One reason string covers not-a-regular-file, not executable, and some symlink oddities, so operators or classifiers may assume `chmod +x` is always the fix when remediation should differ (directory, fifo, symlink target not a normal executable script).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Either split distinct FAILURE_REASON values for non-regular vs non-executable, or document explicitly in run-relevant-checks-captured.md (and mirror in SKILL.md lists) that 126 is the umbrella for any non-invokable check script path.

---

**Merge map (input → output):**  
1, 7, 13, 24 → FINDING_1 · 2 → FINDING_2 · 3, 16, 25 → FINDING_3 · 4, 21 → FINDING_4 · 5 → FINDING_5 · 6 → FINDING_6 · 8 → FINDING_7 · 9 → FINDING_8 · 10, 15 → FINDING_9 · 11, 17 → FINDING_10 · 12 → FINDING_11 · 14 → FINDING_12 · 18, 19 → FINDING_13 · 23 → FINDING_14 · 20 → FINDING_15 · 22 → FINDING_16  

Because this output contains `### FINDING_N:` blocks, **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** anywhere in the file.
