## Goal
Clean up skill-log step headers: remove ✅ completion directives, convert ## Step headers to HTML comments, add missing 🔶 breadcrumbs

## Implementation Plan

### Goal
Clean up skill-log step headers across all 19+ skills: remove ✅ completion directives, convert ## Step headers to HTML comments, add missing 🔶 breadcrumbs to orchestrator steps, update progress-reporting.md contract and test harnesses.

### Files to change

#### A. skills/shared/progress-reporting.md
- Remove ✅ from the "Preserved" line and the completion table row
- Remove the elapsed-time examples using ✅
- Add rule: "## Step N — Description" markdown headers MUST be written as HTML comments: `<!-- step:N — Description -->`
- Clarify that 🔶 start breadcrumbs are the only step markers in chat output

#### B. All 19+ SKILL.md files — Part 2: Convert ## Step N headers to HTML comments
Pattern: `## Step N — Description` → `<!-- step:N — Description -->`
Pattern: `### Step Na — Description` → `<!-- step:Na — Description -->`
Files: fix-issue, implement, design, review, research, issue, umbrella, alias, create-skill, compress-skill, simplify-skill, skill-evolver, cleanup, block-issue, show-skill, report-tokens, upgrade-larch, agnix-fix, combine-issues
(Explicitly exclude non-step ## headings like ## Mindset, ## Anti-patterns, ## Known Limitations, etc.)

#### C. SKILL.md files with ✅ print directives — Part 1: Remove them
- fix-issue/SKILL.md (9 ✅): Remove all "Print '✅ N: ...' (<elapsed>)" directives
- implement/SKILL.md (17 ✅): Remove print directives; keep NEVER rule references that describe what NOT to print; remove Rebase Macro M3 ✅ print directive; update Progress Reporting section
- design/SKILL.md (9 ✅): Remove all ✅ print directives
- review/SKILL.md (1 ✅): Remove it
- research/SKILL.md (12 ✅): Remove all ✅ print directives
- issue/SKILL.md (3 ✅): Remove them
- umbrella/SKILL.md (3 ✅): Remove them
- alias/SKILL.md (2 ✅): Remove them
- compress-skill/SKILL.md (1 ✅): Remove it
- skill-evolver/SKILL.md (2 ✅): Remove them
Reference files: design/references/discussion-rounds.md, plan-review.md, plan-review-quick.md, dialectic-execution.md; research/references/research-phase.md

#### D. Add missing 🔶 breadcrumb directives — Part 4 (orchestrator skills only)
- fix-issue/SKILL.md: Add "Print `> **🔶 /fix-issue 0: find & lock**`" (non-umbrella start), "Print `> **🔶 /fix-issue 1: setup**`", "Print `> **🔶 /fix-issue 2: read details**`", "Print `> **🔶 /fix-issue 8: cleanup**`"
- implement/SKILL.md: Add 🔶 for Steps 0, 0.5, 1, 3, 4, 6, 7, 16, 17; Step 5 normal mode
- design/SKILL.md: Add `Print: '> **🔶 /design 0: session setup**'` at Step 0 entry
- review/SKILL.md: Add 🔶 for Steps 0, 1, 2, 3, 4, 5
- research/SKILL.md: Add `Print: '✅ 0: setup — ...'` removal already covered; add 🔶 for step 0

#### E. Test harness update
- skills/fix-issue/scripts/test-fix-issue-step-order.sh:
  - Assertion 3: Change `## Step 0 — Find and Lock` → `<!-- step:0 — Find and Lock -->`
  - Assertion 4: Change `## Step 1 — Setup` → `<!-- step:1 — Setup -->`
  - Remove assertion 6 (✅ 0: find & lock)
  - Update awk block boundaries from `## Step 0` / `## Step 1` → `<!-- step:0` / `<!-- step:1`


## Test plan
- Run `/relevant-checks` after all changes
- Verify: zero `Print '✅` in SKILL.md files
- Verify: zero `^## Step` in SKILL.md files
- Verify: test-fix-issue-step-order passes
