## Plan

Make plan-review semantic dedup explicit in the orchestrator prompt and add a NEVER rule to keep future orchestrators from regressing to string-key clustering.

### Files to modify

- **UPDATED** `skills/design/references/plan-review.md` — in the **Collecting External Reviewer Results** section, replace the one-sentence dedup paragraphs:
  - **Step 2 (in-scope)** new wording: "Deduplicate in-scope findings semantically using main-agent judgment. Read each finding's `what`, `scenario_or_breakage`, and `suggested_fix` fields (from the structured sidecar TSV) and group findings whose underlying concern is the same — even when phrased differently, cited with different `file:line` locations, or tagged with different `focus_area` values. Do NOT mechanically cluster by string keys on `(focus_area, location, what-prefix)` — reviewers routinely phrase the same concern differently, and string-key clustering yields near-zero dedup. Assign each cluster a stable sequential ID (`FINDING_1`, `FINDING_2`, etc.) and note which reviewer(s) proposed each."
  - **Step 3 (OOS)** new wording: "Deduplicate out-of-scope observations semantically using main-agent judgment, applying the same approach as step 2 (read each observation's body fields and group by meaning; do NOT cluster by string keys). Assign each cluster an `OOS_` prefixed ID (`OOS_1`, `OOS_2`, etc.). If the same issue appears in both in-scope and OOS from different reviewers, merge under the in-scope finding (in-scope takes precedence)."
- **UPDATED** `skills/design/SKILL.md` — two edits in the **Anti-patterns** section:
  1. Insert a new NEVER rule #6 immediately after the existing rule #5 (the "NEVER conflate the two timeout families" entry): "**NEVER mechanically dedupe plan-review findings by string-key clustering** (for example, grouping by the tuple `(focus_area, location, what-prefix)` or writing a Python/shell helper to bucket findings by these fields). **Why:** reviewers routinely phrase the same concern differently across slots — different `file:line` citations, different prefix wording, different `focus_area` assignment — so string-key clustering produces near-zero dedup and inflates ballot size with semantic duplicates. The `/review` code-review path uses an LLM-based aggregator (`skills/review/scripts/aggregate-findings.sh`); the `/design` plan-review path has no such helper and the dedup is owned by the orchestrator's main-agent judgment. **How to apply:** read each finding's `what`, `scenario_or_breakage`, and `suggested_fix` fields semantically and group by meaning. If the orchestrator is tempted to write a Python/shell helper to mechanically cluster findings, that temptation itself signals the wrong approach — proceed by reading."
  2. Update the **Design Mindset** preamble bullet that reads "muscle memory for the five rules" to read "muscle memory for the six rules" (count consistency with the new rule #6).

### Approach

- Use `Edit` to replace the two dedup paragraphs in `plan-review.md` (the paragraphs are unique strings on the page so `old_string` matching is unambiguous).
- Use `Edit` to insert NEVER rule #6 after rule #5 in `SKILL.md` (anchor on the full rule #5 paragraph + the blank line that follows it; insert rule #6 + a blank line before the existing `## Pre-Step-0` header).
- Use `Edit` to change "muscle memory for the five rules" → "muscle memory for the six rules" in the Design Mindset section.
- No new files; the optional aggregator helper from the issue's suggested fix #3 is explicitly out-of-scope.
- No parallel changes to `/review` references (the `/review` path already uses `aggregate-findings.sh`, so the asymmetry between `/design` and `/review` prompt language is correct).

### Edge cases

- Rule #4's inline `#4` token remains correct (rule #6 does not displace any earlier rule).
- The new wording must avoid backticks containing leading/trailing whitespace (`markdown-no-space-in-code-span` rule, markdownlint MD038).
- Plan references affected sections by symbol (section headers, rule numbers), not absolute line numbers (`drift-prone-prose-in-docs`).
- Pre-edit grep for "five rules" / "five NEVER" anywhere in the repo to catch any other doc carrying the same hardcoded count; update or note matches in the same change.

### Failure modes

1. **CI lint regression on the new prose** — `markdownlint` MD038 (code spans with leading/trailing whitespace) is the most likely failure given several backticked tokens in the new wording. **Earliest signal**: `bash scripts/relevant-checks.sh` reports MD038. **Mitigation**: shift any space outside the backticks before submitting.
2. **Stale count-bearing prose elsewhere** — if "five rules" appears in another doc it would drift. **Earliest signal**: pre-edit `grep -rn "five rules\|five NEVER" .`. **Mitigation**: update any matches found.
3. **Pinned structural test** — `scripts/test-design-structure.sh` Check #16 is a structural markdown pin over required anchors in `SKILL.md`. **Earliest signal**: `make lint` failing the structure test. **Mitigation**: keep rules #1–#5 byte-identical, insert #6 between rule #5 and the blank line that precedes `## Pre-Step-0`; do not renumber or restructure surrounding prose.

### Testing strategy

- Run `bash scripts/relevant-checks.sh` after the edits.
- Run `grep -rn "five rules\|five NEVER" .` from the repo root to confirm no other doc carries the old count.
- Manual visual diff (`git diff skills/design/`) to confirm: `plan-review.md` step 1 and surrounding section unchanged; `SKILL.md` rules #1–#5 byte-identical and only rule #6 + the count change touched.

## Acceptance

- [ ] `skills/design/references/plan-review.md` step 2 (in-scope dedup) replaced with the semantic-dedup wording above.
- [ ] `skills/design/references/plan-review.md` step 3 (OOS dedup) replaced with the symmetric semantic-dedup wording above.
- [ ] `skills/design/SKILL.md` contains a new NEVER rule #6 immediately after rule #5, with the canonical "Why" / "How to apply" body and no specific "~30 raw findings" threshold.
- [ ] `skills/design/SKILL.md` Design Mindset bullet reads "muscle memory for the six rules" (was "five rules").
- [ ] Existing NEVER rules #1–#5 are byte-identical (verified via `git diff`).
- [ ] `bash scripts/relevant-checks.sh` exits zero.
- [ ] `grep -rn "five rules\|five NEVER" .` returns no matches that refer to the design-skill NEVER list.

diff_lines: 22
