# PR Body Template

**Consumer**: `/implement` Step 9a (PR body composition).

**Contract**: Authoritative source for the slim PR body markdown scaffold on a Phase 3+ tracked run. Section headers must NOT drift — downstream tooling treats `Closes #<N>` as the PR-to-tracking-issue linkage. `larch-logs/implement/<RUN_ID>/` owns all rich report content (voting tallies, OOS pipeline output, execution issues, run statistics, version bump reasoning); this template owns only the slim PR projection. Blank lines immediately after opening `<summary>` tags and before closing `</details>` tags are load-bearing for GitHub Markdown rendering.

**When to load**: before writing `$IMPLEMENT_TMPDIR/pr-body.md` in Step 9a. Do NOT load in any other step.

**Sibling**: `skills/implement/references/summary-comment-template.md` owns the marker-keyed tracking-issue summaries that point to the committed larch-log content.

---

## PR Body Template

```markdown
## Summary
<1-3 bullet points in past tense describing what was changed and why (e.g., "Refactored X to improve Y", not "Refactor X to improve Y")>

<details><summary>Architecture Diagram</summary>

<the Architecture Diagram read from ARCHITECTURE_DIAGRAM_FILE in the design manifest. Sanitize the file before inclusion. Copy the mermaid code fence from the file only when sanitizer accepts it. If ARCHITECTURE_DIAGRAM_FILE is absent, unreadable, or rejected, write "Architecture diagram not available.">

</details>

<details><summary>Code Flow Diagram</summary>

<the Code Flow Diagram read from $IMPLEMENT_TMPDIR/code-flow-diagram.md. Sanitize the file before inclusion. Copy the mermaid code fence from the file only when sanitizer accepts it. If the Code Flow Diagram was not generated (generation failed, quick mode, or sanitizer rejection), write "Code flow diagram not available.">

</details>

<details><summary>Test plan</summary>

<bulleted checklist of testing steps>

</details>

Closes #<TRACKING_ISSUE_NUMBER>

Generated with [Claude Code](https://claude.com/claude-code)
```

---

## Composition notes

- `<TRACKING_ISSUE_NUMBER>` is `$ISSUE_NUMBER` from Step 0.5 — set on all four branches when the path succeeds (Branch 1 sentinel reuse, Branch 2 `--issue` adoption, Branch 3 PR-body recovery, Branch 4 immediate first-remote-write). On degraded runs (`repo_unavailable=true` OR Step 0.5 Branch 4 create-issue/metadata-summary/sentinel failure set `deferred=true` with `$ISSUE_NUMBER` unset), Step 9a **omits the `Closes #<TRACKING_ISSUE_NUMBER>` line entirely** and replaces it with the single prose line `_No tracking issue — auto-close N/A._` so the PR body stays well-formed and GitHub does not encounter a malformed `Closes #...` reference.
- Diagram source files are validated with `scripts/sanitize-mermaid-fragment.sh --from-md` before inclusion. Rejected diagrams are replaced with the matching placeholder and logged to `execution-issues.md` as a `Warnings` entry with public-safe `REASON_TOKEN` values.
- The `Closes #<N>` line is load-bearing for three consumers: (1) GitHub's auto-close-on-merge behavior (closes the tracking issue when the PR merges — this is the sole mechanism `/fix-issue` Step 6a relies on for PR-path issue closure); (2) Step 0.5 Branch 3 (PR-body-recovery) uses the FIRST `Closes #<N>` match on an existing PR body to adopt the same tracking issue on a subsequent session; (3) consumers that scrape the issue body for a merged-PR link use the `--pr-url` backfill written by `/fix-issue` Step 3 / 6b (not the PR path).
- Rich report content (voting tallies, execution issues, OOS list, run statistics, version bump reasoning) is written through `scripts/larch-log.sh` batches, not to this PR body. Diagrams are posted only to the tracking issue via the `larch:diagrams` summary comment. See `skills/implement/references/summary-comment-template.md` for the four marker-keyed tracking-issue summary comments.
