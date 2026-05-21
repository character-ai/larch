### FINDING_1: **correctness** `.claude/skills/audit-runs/scans.tsv:5` — The jq fragment is valid for normal rows where `id` and `prose_body` are JSON strings, but `(.id|startswith("REJ_"))` and `(.prose_body|test("…"))` throw on `null`/non-string inputs (`startswith` and `test` require strings), so a malformed or partial JSONL line could make a manual `jq` pass over the file fail instead of treating the row as non-matching. **Suggested fix:** Harden the predicate with string defaults, e.g. `((.id//"")|type=="string" and startswith("REJ_"))` and `((.prose_body//"")|test("### FINDING_[0-9A-Za-z_]+:"))`, matching how `category` already uses `(.category//"")`.
- **Reviewer**: dyn-scan-jq-filter-output.txt
- **Concern**: - **correctness** `.claude/skills/audit-runs/scans.tsv:5` — The jq fragment is valid for normal rows where `id` and `prose_body` are JSON strings, but `(.id|startswith("REJ_"))` and `(.prose_body|test("…"))` throw on `null`/non-string inputs (`startswith` and `test` require strings), so a malformed or partial JSONL line could make a manual `jq` pass over the file fail instead of treating the row as non-matching. **Suggested fix:** Harden the predicate with string defaults, e.g. `((.id//"")|type=="string" and startswith("REJ_"))` and `((.prose_body//"")|test("### FINDING_[0-9A-Za-z_]+:"))`, matching how `category` already uses `(.category//"")`.
- **Suggested revision**: Address the concern above.

### FINDING_2: **correctness** `scripts/compose-review-findings.sh:70-71` — Rejected inner headings are appended whenever a line matches `^###[[:space:]]` (see the `code-review-rejected` path around lines 242–245), so the body can legally contain multiple spaces after `###` (for example `###   FINDING_1:`). The new `extract_category` rule only matches `/^### FINDING_/` (exactly one space before `FINDING_`) and strips the prefix with `sub(/^### FINDING_[^:]*:/, "")`, so those bodies never hit the triple-hash branch and can still end up with an empty `category` even though a `### … FINDING_…:` header is present—exactly the failure mode the scan is meant to catch. **Suggested fix:** Align the awk rule and `sub` with the parser by using a prefix pattern such as `/^###[[:space:]]+FINDING_/` and `sub(/^###[[:space:]]+FINDING_[^:]*:/, "")` (and keep trimming leading whitespace after the prefix as today).
- **Reviewer**: dyn-scan-jq-filter-output.txt
- **Concern**: - **correctness** `scripts/compose-review-findings.sh:70-71` — Rejected inner headings are appended whenever a line matches `^###[[:space:]]` (see the `code-review-rejected` path around lines 242–245), so the body can legally contain multiple spaces after `###` (for example `###   FINDING_1:`). The new `extract_category` rule only matches `/^### FINDING_/` (exactly one space before `FINDING_`) and strips the prefix with `sub(/^### FINDING_[^:]*:/, "")`, so those bodies never hit the triple-hash branch and can still end up with an empty `category` even though a `### … FINDING_…:` header is present—exactly the failure mode the scan is meant to catch. **Suggested fix:** Align the awk rule and `sub` with the parser by using a prefix pattern such as `/^###[[:space:]]+FINDING_/` and `sub(/^###[[:space:]]+FINDING_[^:]*:/, "")` (and keep trimming leading whitespace after the prefix as today).
- **Suggested revision**: Address the concern above.

### FINDING_3: **correctness** `scripts/compose-review-findings.sh:70-90` — For `strict=0` (including all `rejected` records), the new `/^### FINDING_/` rule prints the first colon-delimited candidate and always `exit`s, so a `prose_body` whose first `### FINDING_…` line is a non–focus-area title (for example the same shape as `scripts/test-compose-review-findings.sh:211` in the existing “body reviewer attribution” fixture) can no longer fall through to a later canonical `## …` heading that the previous awk-only-`##` logic would have treated as the category source, which is a plausible regression for rare mixed layouts. **Suggested fix:** When `strict=0`, if the `### FINDING_` candidate is not one of the five canonical focus-area tags, use `next` instead of `exit` (and only `exit` after emitting), so scanning can still reach a subsequent `##` line while preserving the fix for bodies that only have the triple-hash inner heading with a real tag.
- **Reviewer**: dyn-test-coverage-output.txt
- **Concern**: - **correctness** `scripts/compose-review-findings.sh:70-90` — For `strict=0` (including all `rejected` records), the new `/^### FINDING_/` rule prints the first colon-delimited candidate and always `exit`s, so a `prose_body` whose first `### FINDING_…` line is a non–focus-area title (for example the same shape as `scripts/test-compose-review-findings.sh:211` in the existing “body reviewer attribution” fixture) can no longer fall through to a later canonical `## …` heading that the previous awk-only-`##` logic would have treated as the category source, which is a plausible regression for rare mixed layouts. **Suggested fix:** When `strict=0`, if the `### FINDING_` candidate is not one of the five canonical focus-area tags, use `next` instead of `exit` (and only `exit` after emitting), so scanning can still reach a subsequent `##` line while preserving the fix for bodies that only have the triple-hash inner heading with a real tag.
- **Suggested revision**: Address the concern above.

### FINDING_4: **correctness** `scripts/compose-review-findings.sh:70-90` — The new `/^### FINDING_/` rule runs before `^## /` and, on the first matching inner-heading line, takes the text after the stripped `### FINDING_<id>:` prefix and treats everything up to the next `:` as the category, or the whole remainder if there is no `:` (same structure as the `^## /` branch). For rejected blocks whose inner line is the title-only shape `### FINDING_<id>: <free-form title>` with no second `:` (for example the existing fixture `### FINDING_18: Review finding title` in `scripts/test-compose-review-findings.sh:241-245`), that remainder is a sentence-style title, not a focus-area tag; the script previously left `category` empty because no `##` line matched, but with this change `category` becomes non-empty junk (e.g. `Review finding title`), which is a behavioral regression for any consumer that assumed “non-empty category means a real focus-area tag” or that relied on emptiness for title-only rejections. **Suggested fix:** Narrow the `### FINDING_` branch so single-colon bodies only yield a category when the candidate is one of the five canonical tags (matching the spirit of the new `rej-category-blank` guardrail), or require a second `:` in the line (true `### FINDING_n: <tag>: <location>` form) before treating the first segment as `category`, while still allowing the documented `### FINDING_n: architecture` case if you explicitly whitelist the tag when no second colon is present.
- **Reviewer**: dyn-awk-parsing-output.txt
- **Concern**: - **correctness** `scripts/compose-review-findings.sh:70-90` — The new `/^### FINDING_/` rule runs before `^## /` and, on the first matching inner-heading line, takes the text after the stripped `### FINDING_<id>:` prefix and treats everything up to the next `:` as the category, or the whole remainder if there is no `:` (same structure as the `^## /` branch). For rejected blocks whose inner line is the title-only shape `### FINDING_<id>: <free-form title>` with no second `:` (for example the existing fixture `### FINDING_18: Review finding title` in `scripts/test-compose-review-findings.sh:241-245`), that remainder is a sentence-style title, not a focus-area tag; the script previously left `category` empty because no `##` line matched, but with this change `category` becomes non-empty junk (e.g. `Review finding title`), which is a behavioral regression for any consumer that assumed “non-empty category means a real focus-area tag” or that relied on emptiness for title-only rejections. **Suggested fix:** Narrow the `### FINDING_` branch so single-colon bodies only yield a category when the candidate is one of the five canonical tags (matching the spirit of the new `rej-category-blank` guardrail), or require a second `:` in the line (true `### FINDING_n: <tag>: <location>` form) before treating the first segment as `category`, while still allowing the documented `### FINDING_n: architecture` case if you explicitly whitelist the tag when no second colon is present.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] - **architecture** `scripts/compose-review-findings.sh:187-202` — `flush_pending` can still prepend a synthetic `## $pending_title` when `pending_title` is set; today `code-review-rejected` / `plan-review-rejected` never set `pending_title`, so REJ bodies still reach `extract_category` with a leading `### FINDING_` line as intended. **Suggested fix:** None required for this change; if a future path ever prepends `##` ahead of an inner `### FINDING_` line for REJ records, reorder or extend `extract_category` so the triple-hash line wins over a decorative `##` title line.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. - **architecture** `scripts/compose-review-findings.sh:187-202` — `flush_pending` can still prepend a synthetic `## $pending_title` when `pending_title` is set; today `code-review-rejected` / `plan-review-rejected` never set `pending_title`, so REJ bodies still reach `extract_category` with a leading `### FINDING_` line as intended. **Suggested fix:** None required for this change; if a future path ever prepends `##` ahead of an inner `### FINDING_` line for REJ records, reorder or extend `extract_category` so the triple-hash line wins over a decorative `##` title line.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] - **risk-integration** `.claude/skills/audit-runs/scans.tsv` — `jsonl-field` patterns are descriptive filters for the audit workflow (same class as existing rows such as `oos-category-mangle`); this diff does not add code that evaluates the TSV as shell. **Suggested fix:** N/A; any future automation that feeds these strings into a shell should use argument-safe `jq` invocation (pre-existing integration concern).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. - **risk-integration** `.claude/skills/audit-runs/scans.tsv` — `jsonl-field` patterns are descriptive filters for the audit workflow (same class as existing rows such as `oos-category-mangle`); this diff does not add code that evaluates the TSV as shell. **Suggested fix:** N/A; any future automation that feeds these strings into a shell should use argument-safe `jq` invocation (pre-existing integration concern). The precomputed diff also adds `larch-logs/implement/D5F7F883-.../` with placeholder `operator_cwd` / `operator_repo_root` and issue 2479 metadata; per your instructions, that is intentional run-log material, not a security or scope problem.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] The branch also adds committed implement run artifacts under `larch-logs/implement/D5F7F883-3EED-40B7-BD32-EBEFDF4A1248/` (see diff hunks for `manifest.json`, `parent-issue.md`, etc.), which is unrelated noise for the stated #2479 fix and may be undesirable for reviewers and repo size even though it does not affect runtime correctness of `extract_category`.
- **Reviewer**: dyn-awk-parsing-output.txt
- **Concern**: - The branch also adds committed implement run artifacts under `larch-logs/implement/D5F7F883-3EED-40B7-BD32-EBEFDF4A1248/` (see diff hunks for `manifest.json`, `parent-issue.md`, etc.), which is unrelated noise for the stated #2479 fix and may be undesirable for reviewers and repo size even though it does not affect runtime correctness of `extract_category`.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] The new block in `scripts/test-compose-review-findings.sh:221-242` is aligned with `synthetic_id` in `scripts/compose-review-findings.sh:178-185` and the `code-review-rejected` counter in `scripts/compose-review-findings.sh:232-236`: two successive `### [rejected] …` headers in one `rejected-findings-full.md` yield `REJ_C1` and `REJ_C2` when `round_num` is empty. `record_field_by_id` in `scripts/test-compose-review-findings.sh:25-28` uses `jq`’s `// empty`, so a missing `category` becomes an empty string and the `[[ "$(record_field_by_id …)" == "architecture" ]]` / `security` checks would fail loudly rather than pass on a missing id. The following “preserve inner headings inside OOS code-review blocks” case in `scripts/test-compose-review-findings.sh:244-260` still prepends a synthetic `## …` title via `flush_pending` in `scripts/compose-review-findings.sh:191-192`, so `extract_category` hits the `##` rule on the first line before any inner `### FINDING_1:` line; it does not assert `category`, and the new triple-hash branch does not change that flow. The branch diff also adds unrelated `larch-logs/implement/D5F7F883-3EED-40B7-BD32-EBEFDF4A1248/*` run artifacts (see pre-computed diff), which is repository hygiene rather than functional correctness of the compose fix.
- **Reviewer**: dyn-test-coverage-output.txt
- **Concern**: - The new block in `scripts/test-compose-review-findings.sh:221-242` is aligned with `synthetic_id` in `scripts/compose-review-findings.sh:178-185` and the `code-review-rejected` counter in `scripts/compose-review-findings.sh:232-236`: two successive `### [rejected] …` headers in one `rejected-findings-full.md` yield `REJ_C1` and `REJ_C2` when `round_num` is empty. `record_field_by_id` in `scripts/test-compose-review-findings.sh:25-28` uses `jq`’s `// empty`, so a missing `category` becomes an empty string and the `[[ "$(record_field_by_id …)" == "architecture" ]]` / `security` checks would fail loudly rather than pass on a missing id. The following “preserve inner headings inside OOS code-review blocks” case in `scripts/test-compose-review-findings.sh:244-260` still prepends a synthetic `## …` title via `flush_pending` in `scripts/compose-review-findings.sh:191-192`, so `extract_category` hits the `##` rule on the first line before any inner `### FINDING_1:` line; it does not assert `category`, and the new triple-hash branch does not change that flow. The branch diff also adds unrelated `larch-logs/implement/D5F7F883-3EED-40B7-BD32-EBEFDF4A1248/*` run artifacts (see pre-computed diff), which is repository hygiene rather than functional correctness of the compose fix.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] `sub(/^### FINDING_[^:]*:/, "")` followed by `index($0, ":")` is consistent with POSIX awk behavior (`sub` updates `$0` before `index` runs); no stale-field issue there, and `exit` prevents the `^## /` rule from running on the same record once a `### FINDING_` line has matched.
- **Reviewer**: dyn-awk-parsing-output.txt
- **Concern**: - `sub(/^### FINDING_[^:]*:/, "")` followed by `index($0, ":")` is consistent with POSIX awk behavior (`sub` updates `$0` before `index` runs); no stale-field issue there, and `exit` prevents the `^## /` rule from running on the same record once a `### FINDING_` line has matched.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] architecture: .claude/skills/audit-runs/SKILL.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Scan table prose lags `scans.tsv` for new rej-category-blank row Operators relying only on the markdown table might miss the new audit signal. Update the SKILL scan table when convenient (not required by this diff).
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] code-quality: .claude/skills/audit-runs/SKILL.md:75-88
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Scan baseline table omits rej-category-blank Operators reading SKILL.md instead of scans.tsv may not know the new audit signal exists. Add a row to the markdown table when convenient; not introduced by this diff’s touched files.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] code-quality: larch-logs/implement/D5F7F883-3EED-40B7-BD32-EBEFDF4A1248/manifest.json:13
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] manifest status in-progress in flushed log Intentional larch-logs flush per policy; cosmetic snapshot only Operator may normalize status when convenient; not part of #2479 fix
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] risk-integration: .claude/skills/audit-runs/SKILL.md:75-88
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Scan baseline markdown table omits the new rej-category-blank row present in scans.tsv. Operators reading only SKILL.md miss the new guardrail; file not touched by this branch. Update SKILL scan table when editing that doc, or regenerate from scans.tsv.
- **Suggested revision**: Address the concern above.

### FINDING_14: architecture: scripts/compose-review-findings.sh:80-115
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Duplicated five-tag whitelist across two awk rules Maintenance drift if tag set changes Single shared whitelist check in awk
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: scripts/compose-review-findings.sh:70-120
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated awk strict/print/exit logic for ### FINDING_ vs ## category extraction Future edits to whitelist or trim behavior can update one branch and miss the other, silently skewing REJ vs accepted categories. Collapse to one post-parse block for candidate normalization and printing, or share an awk helper.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: .claude/skills/audit-runs/scans.tsv:5
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] rej-category-blank jq test uses FINDING_[0-9A-Za-z_]+: while awk uses FINDING_[^:]*: for the id segment. Malformed ### FINDING_: heading edge case could yield blank category without tripping the scan regex. Align test() regex with awk id stripping or document the narrower scan on purpose.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: .claude/skills/audit-runs/scans.tsv:5
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] rej-category-blank uses .prose_body|test without null guard jq errors on null prose_body and can fail the scan or jq batch Coalesce with ( .prose_body // "" ) before test()
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/compose-review-findings.sh:69-88
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Triple-hash extract_category treats any no-second-colon remainder after FINDING_ as category under strict=0. Existing fixture body ### FINDING_18: Review finding title (j-impl rejected test) yields category Review finding title instead of empty, contradicting FINDING_N: <category>: intent and changing JSONL from prior empty category. Narrow ### FINDING_ parsing (e.g. require second colon or whitelist five tags for REJ) and lock behavior with an assertion on REJ_C1 category in that test.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: scripts/compose-review-findings.sh:70-72
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] awk /^### FINDING_/ is stricter than parse_artifact ^###[[:space:]]+FINDING_ Multi-space after ### leaves category blank despite FINDING header in body Use /^###[[:space:]]+FINDING_/ aligned with parser
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: scripts/compose-review-findings.sh:70-89
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] First ### FINDING_ line always parsed for category per plan awk Legacy inner heading like ### FINDING_18: Review finding title (no category:location second colon) now yields non-empty category with free text; previously empty for REJ_* Align with #2479: either accept as best-effort or gate on second colon / whitelist for this path and assert in existing title-only fixture
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: scripts/compose-review-findings.sh:70-89
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] ### FINDING_ awk rule can run when the inner-heading prefix strip did not match Malformed prose line matching /^### FINDING_/ without ### FINDING_<id>: can yield the entire line as category when strict=0. Guard on successful sub() or use a stricter anchored regex before treating the line as an inner FINDING heading.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: scripts/compose-review-findings.sh:70-90
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Triple-hash awk anchor is stricter than rejected inner-heading matcher on whitespace after `###` Producers using tabs or multiple spaces before `FINDING_` could still populate prose_body but leave category empty. Match flexible whitespace after `###` in awk (align with `^###[[:space:]]+` semantics) before parsing the FINDING id and category.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/test-compose-review-findings.sh:221-242
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing regression for plan-listed no-second-colon triple-hash shape CI could stay green if the no-colon remainder branch in extract_category regressed for REJ_* bodies. Add a harness row using `### FINDING_<id>: <canonical-tag>` with no trailing location colon and assert `category` on the synthetic REJ id.
- **Suggested revision**: Address the concern above.

