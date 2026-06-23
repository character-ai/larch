### FINDING_1: Files-to-modify exemplar omits quoted missing-table warning
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Generic
- **Severity**: important
- **Concern**: The `skills/design/SKILL.md` Files-to-modify copy-paste exemplar (lines 141–147) still jumps from `- if absent, print exactly:` straight to `- parse .step3-review-result.env` with no quoted missing-table warning between them. Approach lines 37–38 and plan line 152 pin the exact string `**⚠ Reviewer status table omitted: pre-rendered table not found.**`, but the exemplar does not embed it. An implementer following only the checklist exemplar can omit, paraphrase, or resurrect the retired round-unbound warning, leaving Step 3 silent or wrong when `reviewer-status-table.txt` is absent. This leaves the round-4 FINDING_2 fix incomplete across all three compact-table sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Insert a dedicated exemplar bullet immediately after `- if absent, print exactly:` with the literal `**⚠ Reviewer status table omitted: pre-rendered table not found.**` (matching Approach lines 37-38) before the parse-env bullet, and mirror the same three-bullet tail (Read tool, plain orchestrator emit, no Bash/Python print, quoted warning, then parse env) in the Progress Reporting and both Step 3 post-notification replacement specs.
  - From Cursor-Innovation: Insert the nested warning bullet under `if absent, print exactly:` in the exemplar: `- **⚠ Reviewer status table omitted: pre-rendered table not found.**` before the parse-env bullet, matching Approach lines 37-38.
  - From Cursor-Pragmatic: Add the quoted bullet between the two exemplar lines: `**⚠ Reviewer status table omitted: pre-rendered table not found.**` (match Approach lines 37-38 verbatim).
  - From Cursor-Requirements: Add a sub-bullet under "if absent, print exactly:" in the lines 141-147 exemplar (and mirror it in all three site examples) with the exact quoted line **⚠ Reviewer status table omitted: pre-rendered table not found.** so the copy-paste contract matches Approach lines 37-38 and edge-case line 180.
  - From Codex-Generic: Add the literal `**⚠ Reviewer status table omitted: pre-rendered table not found.**` as its own bullet directly under "if absent, print exactly:" in the Files-to-modify SKILL.md contract


