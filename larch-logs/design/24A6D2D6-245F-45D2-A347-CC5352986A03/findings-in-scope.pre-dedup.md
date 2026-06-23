### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:141-147
- **Concern**: SKILL.md copy-paste exemplar still omits the quoted missing-table warning (round-4 FINDING_2 incomplete). Scenario: Round-4 accepted FINDING_2 asked for the warning literal in the Files-to-modify checklist. The plan adds that rule at line 152 and pins the exact string in Approach lines 37-38, but the exemplar block copied into all three compact-table sites still jumps from `- if absent, print exactly:` straight to `- parse .step3-review-result.env` with no quoted warning bullet between them. An implementer following only the exemplar can again omit, paraphrase, or resurrect the retired round-unbound warning.
- **Proposed resolution**: Insert a dedicated exemplar bullet immediately after `- if absent, print exactly:` with the literal `**⚠ Reviewer status table omitted: pre-rendered table not found.**` (matching Approach lines 37-38) before the parse-env bullet, and mirror the same three-bullet tail (Read tool, plain orchestrator emit, no Bash/Python print, quoted warning, then parse env) in the Progress Reporting and both Step 3 post-notification replacement specs.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:141-147
- **Concern**: Files-to-modify exemplar still omits the quoted missing-table warning (round-4 FINDING_2 fix incomplete). Scenario: The Approach pins the literal at lines 37-38 and line 152 requires each compact-table site to carry it on its own bullet, but the copy-paste exemplar at lines 146-147 still has a dangling `- if absent, print exactly:` followed immediately by `- parse .step3-review-result.env`. An implementer working from the Files checklist can ship all three Step 3 sites without the warning, paraphrase it, or resurrect the retired round-unbound message.
- **Proposed resolution**: Insert the nested warning bullet under `if absent, print exactly:` in the exemplar: `- **⚠ Reviewer status table omitted: pre-rendered table not found.**` before the parse-env bullet, matching Approach lines 37-38.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/design/SKILL.md:141-147
- **Concern**: Compact-table exemplar does not retire the step-2 `using this data path` header. Scenario: The exemplar replaces TSV primary/fallback bullets but does not say to change the numbered step-2 title `**Print the compact table once** using this data path:`. That header still implies orchestrator-side TSV selection. It can survive in all three sites even when nested bullets are updated, reintroducing manual-render semantics beside the Read-only contract.
- **Proposed resolution**: Add an explicit Files-to-modify bullet: replace the step-2 title with `**Emit the compact table once**` (or equivalent) and drop `using this data path`; the only source is Read on `$DESIGN_TMPDIR/reviewer-status-table.txt`.



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:141-147
- **Concern**: Files-to-modify SKILL.md exemplar still omits the quoted missing-table warning literal. Scenario: Round-4 FINDING_3 added the rule at plan line 152 and Approach lines 37-38 pin the exact string, but the copy-paste exemplar at lines 141-147 still jumps from "if absent, print exactly:" straight to "parse .step3-review-result.env". An implementer following only the checklist exemplar can recreate the dangling-warning defect the prior round flagged.
- **Proposed resolution**: Add the quoted bullet between the two exemplar lines: `**⚠ Reviewer status table omitted: pre-rendered table not found.**` (match Approach lines 37-38 verbatim).



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:49;plan.txt:148-157
- **Concern**: Progress Reporting compact-table intro and Step 3 item-2 headers still say "Print the compact table once" outside the scoped rewrite. Scenario: The plan scopes legend removal to Progress Reporting lines 64-69 and replaces post-notification bullets in the exemplar, but line 49 ("Print the compact table once") and all three numbered step-2 headers ("Print the compact table once using this data path:") sit outside that range and are not explicitly retired. Surviving "print/render" language conflicts with the read-only Read-tool emit contract and can leave orchestrator-side TSV rendering instructions in place even when bullets below are updated.
- **Proposed resolution**: Require all three compact-table sites to rename step 2 to an emit-only header (for example "Emit the pre-rendered reviewer-status table once") and rewrite line 49 to state the only output is the verbatim Read of `$DESIGN_TMPDIR/reviewer-status-table.txt`; delete any remaining "print/render from TSV" phrasing in those headers.



### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:141-147
- **Concern**: SKILL.md copy-paste exemplar still omits the pinned missing-table warning literal (round-4 fix incomplete). Scenario: The Files-to-modify exemplar at lines 141-147 jumps from "if absent, print exactly:" straight to "parse .step3-review-result.env" with no quoted warning line between them. Line 152 forbids that dangling shape but does not embed the literal in the exemplar. Approach lines 37-38 pin **⚠ Reviewer status table omitted: pre-rendered table not found.** An implementer copying only the checklist exemplar can omit, paraphrase, or resurrect the retired round-unbound warning, leaving Step 3 silent or wrong when reviewer-status-table.txt is absent.
- **Proposed resolution**: Add a sub-bullet under "if absent, print exactly:" in the lines 141-147 exemplar (and mirror it in all three site examples) with the exact quoted line **⚠ Reviewer status table omitted: pre-rendered table not found.** so the copy-paste contract matches Approach lines 37-38 and edge-case line 180.



### FINDING_7:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:141-147
- **Concern**: Prior accepted fix remains incomplete: SKILL.md replacement contract still omits the warning literal in the copyable bullet list. Scenario: The SKILL.md checklist still says "if absent, print exactly:" and then jumps to parsing `.step3-review-result.env`; an implementer following that checklist can omit or paraphrase the required missing-table warning
- **Proposed resolution**: Add the literal `**⚠ Reviewer status table omitted: pre-rendered table not found.**` as its own bullet directly under "if absent, print exactly:" in the Files-to-modify SKILL.md contract



