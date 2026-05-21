### FINDING_1: **code-quality** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:342-344` — The Test 14 comment block still documents the title as `[Run Logs Audit Report <ISO>]`, while the assertions and `SKILL.md` now use Pacific wall time with a numeric offset in the bracket. That mismatch was left behind while the example titles were updated, so the file’s own comments no longer describe what the tests exercise. **Suggested fix:** Update those comment lines to say Pacific ISO with explicit `-07:00`/`-08:00` (or reference `<Pacific-ISO-timestamp>`) so the narrative matches `### Title Format` in `SKILL.md` and the literals in the same test block.
- **Reviewer**: dyn-timezone-semantics-output.txt
- **Concern**: - **code-quality** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:342-344` — The Test 14 comment block still documents the title as `[Run Logs Audit Report <ISO>]`, while the assertions and `SKILL.md` now use Pacific wall time with a numeric offset in the bracket. That mismatch was left behind while the example titles were updated, so the file’s own comments no longer describe what the tests exercise. **Suggested fix:** Update those comment lines to say Pacific ISO with explicit `-07:00`/`-08:00` (or reference `<Pacific-ISO-timestamp>`) so the narrative matches `### Title Format` in `SKILL.md` and the literals in the same test block.
- **Suggested revision**: Address the concern above.

### FINDING_2: **code-quality** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:77-79` — The Test 3 section header was renamed to `since <ISO8601-instant>` (matching `SKILL.md`), but the progress `echo` still prints `since <ISO>`, so the harness text disagrees with the skill’s public naming for the same verbal form. **Suggested fix:** Change the `echo` line to use the same `ISO8601-instant` wording (or a neutral phrase like `since <timestamp>`) so operators grepping the test output stay aligned with `SKILL.md`.
- **Reviewer**: dyn-timezone-semantics-output.txt
- **Concern**: - **code-quality** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:77-79` — The Test 3 section header was renamed to `since <ISO8601-instant>` (matching `SKILL.md`), but the progress `echo` still prints `since <ISO>`, so the harness text disagrees with the skill’s public naming for the same verbal form. **Suggested fix:** Change the `echo` line to use the same `ISO8601-instant` wording (or a neutral phrase like `since <timestamp>`) so operators grepping the test output stay aligned with `SKILL.md`.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] **Commits on branch since merge-base with `main`:** `4af2b8c8 Use PDT/PST offset timestamps in audit-runs report title and frontmatter` and `52190c1f Address code review feedback (round 1)`.
- **Reviewer**: dyn-timezone-semantics-output.txt
- **Concern**: - **Commits on branch since merge-base with `main`:** `4af2b8c8 Use PDT/PST offset timestamps in audit-runs report title and frontmatter` and `52190c1f Address code review feedback (round 1)`.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] **code-quality / companion doc drift:** [.claude/skills/audit-runs/scripts/test-audit-runs.md](.claude/skills/audit-runs/scripts/test-audit-runs.md) still lists `since <ISO>` in the “What is tested” bullet (line 11); it was not updated in the provided diff while `SKILL.md` standardized on `ISO8601-instant`. Low impact, but worth aligning when touching this area again.
- **Reviewer**: dyn-timezone-semantics-output.txt
- **Concern**: - **code-quality / companion doc drift:** [.claude/skills/audit-runs/scripts/test-audit-runs.md](.claude/skills/audit-runs/scripts/test-audit-runs.md) still lists `since <ISO>` in the “What is tested” bullet (line 11); it was not updated in the provided diff while `SKILL.md` standardized on `ISO8601-instant`. Low impact, but worth aligning when touching this area again.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] **correctness (scout checklist):** The Pacific examples are arithmetically consistent with US rules for the cited calendar dates: `2026-05-20T12:30-07:00` is the same instant as `2026-05-20T19:30Z` (May is PDT), and `2026-01-15T12:30-08:00` is a valid PST-offset winter example. The branch’s `SKILL.md` text correctly separates the `since <ISO8601-instant>` filter (GitHub-style `Z` or explicit offsets, not tied to Pacific titles) from report `audit_timestamp`/title Pacific convention, and it correctly states that `since last audit` keys off `audited_pr_range.last` then `mergedAt` from the API rather than `audit_timestamp`. The `.claude/skills/audit-runs/` tree contains only `SKILL.md`, `scans.tsv`, and the test harness—no separate runtime script in-repo that could contradict those docs—so there is no implementation-vs-doc mismatch to flag beyond documentation drift noted above.
- **Reviewer**: dyn-timezone-semantics-output.txt
- **Concern**: - **correctness (scout checklist):** The Pacific examples are arithmetically consistent with US rules for the cited calendar dates: `2026-05-20T12:30-07:00` is the same instant as `2026-05-20T19:30Z` (May is PDT), and `2026-01-15T12:30-08:00` is a valid PST-offset winter example. The branch’s `SKILL.md` text correctly separates the `since <ISO8601-instant>` filter (GitHub-style `Z` or explicit offsets, not tied to Pacific titles) from report `audit_timestamp`/title Pacific convention, and it correctly states that `since last audit` keys off `audited_pr_range.last` then `mergedAt` from the API rather than `audit_timestamp`. The `.claude/skills/audit-runs/` tree contains only `SKILL.md`, `scans.tsv`, and the test harness—no separate runtime script in-repo that could contradict those docs—so there is no implementation-vs-doc mismatch to flag beyond documentation drift noted above.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.md:11
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] test-audit-runs.md still says since <ISO> vs SKILL ISO8601-instant. Doc skew for readers of test harness doc only. Update when touching that file.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.md:11
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Doc lists since ISO form name not updated to ISO8601-instant Readers comparing skill vs test harness doc may infer a spec mismatch Align test-audit-runs.md wording with SKILL.md on next edit
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.md:11
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract doc lists since <ISO> not renamed in this branch. Doc readers see a different verbal form than SKILL.md after this merge. Update test-audit-runs.md when convenient to match SKILL.md.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.md:11-20
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Contract doc still says since <ISO> and ISO timestamp inside brackets; not updated with this branch. Docs drift from SKILL.md naming; not introduced in this diff. Update sibling .md in a follow-up PR when touching the harness again.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.md:20
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract still says ISO timestamp inside audit report titles. Wording no longer matches Pacific offset title convention. Rephrase to Pacific offset or Pacific-ISO-timestamp when editing that file.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] code-quality: skills/fix-issue/scripts/test-find-lock-issue.sh:1306
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Fixture audit title still uses Z timestamp None for this PR; optional doc alignment with new title convention Update fixture only if team wants examples to match new spec
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] correctness: .claude/skills/audit-runs/SKILL.md:25
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Args bullet elliptical: merged after audited_pr_range.last reads temporal. Reader may misunderstand until step 3. Clarify in a future edit that last is a PR number; merge cutoff is that PRs mergedAt.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] correctness: .claude/skills/audit-runs/scripts/test-audit-runs.sh:80-86
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Optional timezone in parse_since_ts mirror regex unchanged If copied to real gh filter construction timezone-less values could be ambiguous vs mergedAt string ordering Require explicit Z or numeric offset in a dedicated follow-up if behavior should be strict
- **Suggested revision**: Address the concern above.

### FINDING_14: architecture: .claude/skills/audit-runs/SKILL.md:58-61,.claude/skills/audit-runs/scripts/test-audit-runs.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Feature asked to verify Pacific audit_timestamp vs UTC mergedAt; branch documents audit_timestamp unused on since last audit with no automated invariant. Future SKILL edit could compare audit_timestamp to mergedAt as strings or local times; current tests would not fail. Add explicit test or comment locking since last audit to audited_pr_range.last + mergedAt only.
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:341-346
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test 14 header comments still describe <ISO> and ISO timestamp for audit report titles. Comments contradict SKILL.md Pacific-ISO title spec and mislead maintainers about what the exclusion tests represent. Rewrite the comment block to reference Pacific-ISO-timestamp or explicit offset examples.
- **Suggested revision**: Address the concern above.

### FINDING_16: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:342-346
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Test 14 comment still says generic ISO though titles use Pacific offset. Comment drifts from actual title format. Update comment to Pacific-ISO-timestamp wording.
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:342-348
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Test 14 comments still call the embedded title token <ISO> / ISO timestamp after the skill switched to Pacific-ISO-timestamp wording. Maintainers may mis-sync harness intent with SKILL.md when changing title rules again. Reword comments to Pacific-ISO-timestamp or match SKILL.md placeholder naming exactly.
- **Suggested revision**: Address the concern above.

### FINDING_18: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:342-348
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Test 14 comments still describe <ISO> / ISO timestamp inside audit titles after SKILL.md moved to Pacific-ISO-timestamp. Maintainers may apply the wrong title contract when editing tests or regexes. Reword comments to match SKILL.md Pacific-ISO-timestamp wording.
- **Suggested revision**: Address the concern above.

### FINDING_19: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:342-349
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Test 14 comment still documents audit titles as bracketed ISO Z-style timestamps Maintenance could update exclusion tests or comments based on stale ISO wording while titles are Pacific-offset Rewrite the Test 14 comment block to reference Pacific-ISO-timestamp and unchanged bracket prefix
- **Suggested revision**: Address the concern above.

### FINDING_20: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:344-346
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Test 14 comment still says ISO title token Readers may think UTC Z titles remain canonical Update comment to Pacific-ISO or skill wording
- **Suggested revision**: Address the concern above.

### FINDING_21: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:76-93
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Mixed ISO vs ISO8601-instant wording in Test 3 header vs echo/assert labels. Minor confusion when reading test logs. Align echo and assert descriptions with ISO8601-instant.
- **Suggested revision**: Address the concern above.

### FINDING_22: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:79
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test 3 echo still says since <ISO> while the section header uses ISO8601-instant. Operators or future edits may assume the test documents a different arg name than SKILL.md and miss misalignment when updating parsing. Align the echo text with the section header wording.
- **Suggested revision**: Address the concern above.

### FINDING_23: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:79
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Test 3 echo still prints since <ISO> while the section header says ISO8601-instant. In failing runs the log line misstates which contract is under test. Align echo and labels with ISO8601-instant wording.
- **Suggested revision**: Address the concern above.

### FINDING_24: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:79,88-89
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] echo and labels still say since ISO while header says ISO8601-instant Log drift during failing test triage Align echo/assert labels with ISO8601-instant or neutral wording
- **Suggested revision**: Address the concern above.

### FINDING_25: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:89-91
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Assertion description strings for tests [3] and [3b] still say since <ISO>. Failure output and skim-reading the harness suggest the old ISO label rather than ISO8601-instant. Update the assert message strings to match SKILL.md terminology.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: .claude/skills/audit-runs/scripts/test-audit-runs.sh:344
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Test 14 comment still describes audit title as using <ISO> placeholder after Pacific offset migration. Maintainers may follow the wrong placeholder when editing tests or mirroring SKILL.md. Update comment to <Pacific-ISO-timestamp> or match SKILL Title Format wording.
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: .claude/skills/audit-runs/scripts/test-audit-runs.sh:79
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Test 3 echo still labels the parse suite as since <ISO> while SKILL uses since <ISO8601-instant>. Minor inconsistency between test log output and documented arg terminology. Align echo string with SKILL.md Args naming.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: .claude/skills/audit-runs/SKILL.md:26
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] since instant described as matching GitHub mergedAt forms Operator pastes mergedAt with fractional seconds; verbal since form may not match stated GitHub parity Narrow contract to supported subset or document normalize; align tests/parser if they are normative
- **Suggested revision**: Address the concern above.

