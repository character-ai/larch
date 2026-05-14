## Goal
Remove unnecessary close-issue Step 6a from /fix-issue since GitHub auto-closes on PR merge

## Implementation Plan
## Implementation Plan

Remove the unnecessary `issue-lifecycle.sh close` call from Step 6a (PR path) of `/fix-issue` SKILL.md. On `--merge` runs, GitHub auto-closes the issue via `Closes #N` in the PR body, and `/implement` Step 12a/12b already renames the title to `[DONE]`. Step 6b (NON_PR path) must stay — no PR is merged there so the issue must be explicitly closed. Step 6c (umbrella finalize hook) must remain for both paths.

### Changes

**1. `skills/fix-issue/SKILL.md`**

a) Anti-halt continuation reminder (preamble): Update the Step 6 description. Current text says "Step 6 always invokes `issue-lifecycle.sh close` (and additionally invokes `tracking-issue-write.sh rename` on the NON_PR sub-branch 6b)". Change to: "On the NON_PR sub-branch 6b, Step 6 invokes `issue-lifecycle.sh close` and `tracking-issue-write.sh rename`; on the PR sub-branch 6a, Step 6 runs no Bash calls (GitHub auto-closes the issue on PR merge)".

b) Round-trip detection section (Step 3): Remove the PR-path Step 6a reference. Current text: "before any Step 3 / Step 6 terminal `tracking-issue-write.sh rename --state done`... For PR-path Step 6a, also fetch PR text...". Change to: "before any Step 3 / Step 6b terminal `tracking-issue-write.sh rename --state done`..." and remove the "For PR-path Step 6a" sentence.

c) Step 5a success continuation: Change "`> **🔶 6: close issue**`" to "`> **🔶 6: finalize**`".

d) Step 6 heading: "## Step 6 — Close Issue" → "## Step 6 — Finalize"

e) Step 6 breadcrumb: `Print \`> **🔶 6: close issue**\`` → `Print \`> **🔶 6: finalize**\``

f) Step 6 intro + Step 6a body: Replace the entire intro paragraph (about `issue-lifecycle.sh close` idempotency) and Step 6a section (close call + round-trip/rename) with a brief note that on the PR path, GitHub auto-closes the issue on merge and `/implement` Step 12a/12b already renames the title, so Step 6a is a no-op — proceed directly to Step 6c.

g) Step 6c print: "✅ 6: close issue — #$ISSUE_NUMBER closed" → "✅ 6: finalize — #$ISSUE_NUMBER done"

h) Step 6 continuation: "Closing the issue is not terminal" → "This step is not terminal"

**2. `skills/fix-issue/scripts/step-name-registry.tsv`**
Change `6	close issue` to `6	finalize`.

**3. `skills/fix-issue/scripts/issue-lifecycle.sh`**
Update two comments that reference Step 6a calling close:
- Lines 46-47: Update to reflect Step 6b-only calling close
- Line 359: Update reference from "Step 6" to "Step 6b"

### CI safety
- `test-fix-issue-bail-detection.sh`: Uses `^## Step 6` (prefix) as end boundary of 5a block; `## Step 6 — Finalize` still matches. All assertions target Step 5a content (unchanged). ✓
- `test-fix-issue-step-order.sh`: Doesn't check step 6 TSV name. Preamble "child Bash tool calls into the canonical" phrase preserved. ✓

## Test plan
(no test plan section in plan-file)
