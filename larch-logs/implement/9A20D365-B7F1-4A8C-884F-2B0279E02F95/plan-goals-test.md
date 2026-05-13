## Goal
Remove unnecessary diagram content and larch:* summary marker comments from the /implement orchestrator and /fix-issue detail reader to reduce context pollution.

Reduce context pollution in the /implement orchestrator and /fix-issue detail fetcher.

## Files to modify

1. `skills/implement/SKILL.md` (Step 7a section)
   - Remove the sentence "Print the promoted diagram under a `## Code Flow Diagram` header with a mermaid code fence." from the diagram generation success path.
   - Replace the "Diagrams summary comment — larch:diagrams" subsection with a Bash-block approach that uses file redirection to compose the diagrams comment without loading diagram content into the orchestrator context.

2. `skills/fix-issue/scripts/get-issue-details.sh`
   - Add a jq `select()` filter to skip comments whose first line starts with `<!-- larch:` (mirroring tracking-issue-read.sh lines 396-406).

3. `skills/fix-issue/scripts/get-issue-details.md`
   - Document the larch:* marker filtering in the Output section.

## Approach

Change 1 (SKILL.md inline print removal): Single-sentence deletion from Step 7a's diagram generation success path. Low risk — the diagram is already written to a file and posted via tracking-issue-summary.sh; printing it inline only adds it redundantly to the orchestrator context.

Change 2 (SKILL.md Bash-block composition): Replace the two bullet points in "Diagrams summary comment — larch:diagrams" with:
- A prose description explaining CODE_FLOW_SKIP_REASON should be determined from the earlier skip path
- A Bash block that uses cat + file redirection (no stdout) to compose the summary-diagrams.md file
- An explicit tracking-issue-summary.sh upsert call (already implied but now Bash-block-explicit)

Change 3 (get-issue-details.sh filter): Change the jq pipeline from:
  `.[] | "### Comment by \(.user.login) at \(.created_at)\n\n\(.body)\n"`
to:
  `.[] | select((.body // "" | split("\n")[0] | startswith("<!-- larch:")) | not) | "### Comment by \(.user.login) at \(.created_at)\n\n\(.body)\n"`

This skips comments whose first line is a larch summary marker (metadata, diagrams, plan, final-summary, token-report, lifecycle-marker).

## Edge cases

- The Bash block for diagram composition must handle the case where ARCHITECTURE_DIAGRAM_FILE is empty or points to a missing file (graceful fallback).
- The CODE_FLOW_SKIP_REASON variable in the SKILL.md Bash block is a placeholder that the orchestrator fills in from the earlier skip condition; the value needs to be accurate for each of the three skip cases.
- The jq `split("\n")[0]` correctly gets the first line of a comment body (same approach used in bash via `${cbody%%$'\n'*}`).

## Testing strategy

Run `/relevant-checks` after each file change. No new scripts, so no new sibling .md files required (get-issue-details.md already exists and just needs a sentence added).

Verify the jq filter change manually: the filter `(.body // "" | split("\n")[0] | startswith("<!-- larch:")) | not` means: take body or empty string, split by newlines, take first element, check if it starts with `<!-- larch:`, negate — include only comments that are NOT larch markers.

## Test plan
Run /relevant-checks after each change. Verify the jq filter logic is syntactically correct. Verify the SKILL.md changes preserve the correct behavior (diagram file is still written and posted; the inline print is removed; the Bash composition block uses file redirection).
