### FINDING_1: **correctness** `.claude/skills/audit-runs/scans.tsv:5` — The `rej-category-blank` `pattern` uses `test("### FINDING_[0-9A-Za-z_]+:")`, which only matches a single ASCII space after `###`, while `extract_category` in `scripts/compose-review-findings.sh` matches `^###[[:space:]]+FINDING_` (any run of spaces/tabs). A rejected body whose inner heading is `###␠␠FINDING_1: …` would still yield a blank `category` from the awk rules but would not be detected by this scan (false negative relative to the stated acceptance goal). **Suggested fix:** Narrow the gap by aligning the jq regex with the awk/header grammar, e.g. use `test("###[[:space:]]+FINDING_[0-9A-Za-z_]+:")` (and keep the existing `((.prose_body//"")|…)` plumbing) so the audit signal tracks the same whitespace-flexible header the composer treats as authoritative.
- **Reviewer**: dyn-scan-pattern-output.txt
- **Concern**: - **correctness** `.claude/skills/audit-runs/scans.tsv:5` — The `rej-category-blank` `pattern` uses `test("### FINDING_[0-9A-Za-z_]+:")`, which only matches a single ASCII space after `###`, while `extract_category` in `scripts/compose-review-findings.sh` matches `^###[[:space:]]+FINDING_` (any run of spaces/tabs). A rejected body whose inner heading is `###␠␠FINDING_1: …` would still yield a blank `category` from the awk rules but would not be detected by this scan (false negative relative to the stated acceptance goal). **Suggested fix:** Narrow the gap by aligning the jq regex with the awk/header grammar, e.g. use `test("###[[:space:]]+FINDING_[0-9A-Za-z_]+:")` (and keep the existing `((.prose_body//"")|…)` plumbing) so the audit signal tracks the same whitespace-flexible header the composer treats as authoritative.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/compose-review-findings.sh:68-145` — `extract_category` still feeds `awk` via `<<<"$body"` while `body` is expanded inside double quotes, so the usual Bash rule applies: embedded command substitutions in the string would be interpreted by the shell before `awk` runs. This boundary is unchanged by the branch diff (same here-string wiring as before `extract_category` edits); category logic and tests do not widen that surface in a new way. **Suggested fix:** If you ever harden this path, pass the body on stdin (`printf '%s' "$body" | awk ...`) or use a here-document with a quoted delimiter so the prose is never re-parsed by the shell. ```tsv schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix 1	out_of_scope	latent	security	scripts/compose-review-findings.sh:68-145	Double-quoted here-string <<<"$body" lets Bash interpret command substitutions in the body before awk runs.	Pre-existing on the extract_category path; attacker-shaped prose could only matter if redaction or trust boundaries fail elsewhere. Prefer stdin or quoted here-doc if hardening this helper. ```
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] The branch also adds committed implement run material under `larch-logs/implement/D5F7F883-3EED-40B7-BD32-EBEFDF4A1248/` (manifest, `parent-issue.md`, plan artifacts); that is orthogonal to the REJ category fix and may or may not match your repo’s usual policy for flushed run logs (including placeholder fields such as `<OPERATOR_CWD>` in `manifest.json`).
- **Reviewer**: dyn-scan-pattern-output.txt
- **Concern**: - The branch also adds committed implement run material under `larch-logs/implement/D5F7F883-3EED-40B7-BD32-EBEFDF4A1248/` (manifest, `parent-issue.md`, plan artifacts); that is orthogonal to the REJ category fix and may or may not match your repo’s usual policy for flushed run logs (including placeholder fields such as `<OPERATOR_CWD>` in `manifest.json`).
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] The embedded jq expression was sanity-checked with `jq` on representative objects: it evaluates to a boolean, and `|` / `and` precedence behaves as intended for `REJ_` id filtering and `prose_body` matching when the header uses the common single-space form.
- **Reviewer**: dyn-scan-pattern-output.txt
- **Concern**: - The embedded jq expression was sanity-checked with `jq` on representative objects: it evaluates to a boolean, and `|` / `and` precedence behaves as intended for `REJ_` id filtering and `prose_body` matching when the header uses the common single-space form.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] `.claude/skills/audit-runs/SKILL.md`’s human-readable scan table (around lines 77–88) was not updated to mention the new `rej-category-blank` scan; `scans.tsv` remains the machine registry per that skill, so this is documentation drift rather than a logic bug in the new row itself.
- **Reviewer**: dyn-scan-pattern-output.txt
- **Concern**: - `.claude/skills/audit-runs/SKILL.md`’s human-readable scan table (around lines 77–88) was not updated to mention the new `rej-category-blank` scan; `scans.tsv` remains the machine registry per that skill, so this is documentation drift rather than a logic bug in the new row itself.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: .claude/skills/audit-runs/SKILL.md:75-88
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Scan table omits new rej-category-blank row SKILL.md unchanged this PR; table may drift from scans.tsv Update table when editing SKILL for audits
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: larch-logs/implement/D5F7F883-3EED-40B7-BD32-EBEFDF4A1248/manifest.json:17
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] in-progress implement manifest in flushed run log Pre-existing intentional run-log snapshot noise per docs, not a product bug None
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] risk-integration: larch-logs/implement/D5F7F883-3EED-40B7-BD32-EBEFDF4A1248/manifest.json:1-20
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Flushed implement manifest shows in-progress status and null pr_number Pre-existing chore(larch-logs) snapshot shape; not part of the functional REJ category fix If desired, adjust log flush templates outside this feature scope
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: plan:triple-hash-vs-##-nonstrict
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] implementation_plan text says same whitelist for triple-hash as ## lines under non-strict mode Code intentionally rejects some non-canonical single-colon triple-hash titles while ## lines would still emit a label Align issue/plan wording with the documented stricter triple-hash contract or relax code to match the old plan literally
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/compose-review-findings.sh:134-138
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] is_canonical helper added for ### FINDING_ path but ## strict branch still duplicates five literal tag strings Edits to the canonical tag set risk inconsistent behavior or a missed update in one branch only Use is_canonical(candidate) in the strict ## branch
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: .claude/skills/audit-runs/scans.tsv:5
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] rej-category-blank jq test uses a single-space regex between ### and FINDING_ Prose_body `### FINDING_1: architecture: …` (multiple spaces) yields jq test false while awk still may not match or may match differently, so blank-category bugs aligned with that spacing are not counted by the scan Align test() regex with compose-review-findings.sh whitespace (e.g. ###[[:space:]]+FINDING_)
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: .claude/skills/audit-runs/scans.tsv:5
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] rej-category-blank jq matches any ### FINDING_ header with empty category Title-only inner lines and other valid REJ bodies that intentionally have blank category still match test("### FINDING_[...]:"); jq returns true for REJ_C1 with prose_body "### FINDING_18: Review finding title", contradicting scripts/test-compose-review-findings.sh:220-221 Narrow the regex or add conjuncts so the scan only fires when prose_body contains a category-shaped triple-hash line (e.g. canonical tag plus location colon) while category remains empty
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: .claude/skills/audit-runs/scans.tsv:5
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] rej-category-blank prose_body regex is narrower than extract_category heading whitespace A blank category with a multi-space or tab-separated ### heading could evade the scan while still being a real regression Broaden test() regex to ###[[:space:]]+FINDING_[0-9A-Za-z_]+:
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/compose-review-findings.md:31
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] category contract misstates when category is empty vs non-OOS ## lines and triple-hash REJ lines Operators or tooling infer that any unrecognized tag yields empty category only under OOS strict mode, while REJ rows can still carry arbitrary ##-derived labels and REJ ### lines can be empty for different reasons; strict canonical filtering is not OOS-only Clarify in the contract line: ## vs ### rules, strict=1 only for out_of_scope, and the stricter ### single-colon behavior
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/compose-review-findings.sh:184-186
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Non-strict ## vs ### category contract differs for non-canonical labels Reviewer could expect non-canonical category from a two-colon ### line; extract_category returns empty Add REJ_* regression test for non-canonical two-colon triple-hash line asserting empty category
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/compose-review-findings.sh:63-112
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] ### FINDING_ branch under strict=0 is not equivalent to ## branch for non-canonical two-colon-like titles A reviewer body `### FINDING_1: performance: foo.sh` leaves category empty but `## performance: foo.sh` would populate performance for the same strict=0 path, so downstream consumers see inconsistent category fill for similar prose Document as intentional or unify colon-splitting with the ## path for strict=0
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/compose-review-findings.sh:70-144
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Triple-hash branch is stricter than ^## / in non-strict mode Non-strict ## path returns any non-empty candidate; ### FINDING_ path skips non-canonical single-token remainder without a second colon, so category can differ for analogous labels Align non-strict triple-hash parsing with ## behavior or document the asymmetry in the implementation plan and scripts/compose-review-findings.md
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: .claude/skills/audit-runs/scans.tsv:10
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] rej-category-blank jq matches any ### FINDING_ header in prose_body with blank category Title-only inner lines like ### FINDING_18: Review finding title keep category empty by design but still match test(### FINDING_...); audit scan false-positives vs composer tests Tighten regex or add jq guards so only category-shaped triple-hash lines count
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: .claude/skills/audit-runs/scans.tsv:10
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New jsonl-field jq not covered by automated tests Typo or jq precedence change breaks /larch:audit-runs scans with no CI failure Add minimal jq fixture test or documented smoke check per jsonl-field row
- **Suggested revision**: Address the concern above.

