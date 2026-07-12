### FINDING_1: Stale Step 5c private imports in the lifecycle barrel
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The planned Step 5c migration removes or relocates private trailer helpers from `design_step5c.py`, but `design_lifecycle.py` still eagerly imports them. Because those imports resolve at module load, the refactor can raise `ImportError` and prevent `larch.design.design_lifecycle`, registered `design` CLI verbs, and dependent modules from loading before grammar tests run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/larch/design/design_lifecycle.py` to drop obsolete Step 5c trailer imports or repoint them to `plan_grammar` public APIs; alternatively keep thin backward-compat aliases in `design_step5c.py` only until the barrel is updated. Add an import smoke test that `import larch.design.design_lifecycle` succeeds after the Step 5c refactor.
  - From Cursor-Innovation: Add `### UPDATED: python/larch/design/design_lifecycle.py` to drop stale Step 5c private imports or repoint them to `plan_grammar` public helpers; keep the change limited to the import block
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/design/design_lifecycle.py`: drop removed private re-exports, repoint any retained symbols to `plan_grammar` or thin public Step 5c wrappers, and add a barrel import smoke test so a Step 5c refactor cannot break `larch.design.design_lifecycle` load.

### FINDING_2: Incomplete Step 5c auto-compose trailer subset
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The planned optional-size trailer subset does not include `difficulty`, even though Step 5c auto-compose currently handles it alongside the four optional-size keys. Repointing Step 5c splitting and peeling to the narrower subset could leave `difficulty:` in the body or change trailer ordering and orphan-trailer recovery behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In `plan_grammar.py`, export a documented Step-5c auto-compose subset (optional-size keys plus `difficulty`, still excluding `review_status` / `rounds_completed`) and wire Step 5c split/peel helpers to it explicitly in the `design_step5c.py` plan step

### FINDING_3: Scope extraction can terminate before valid headings and fenced examples
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The planned scope extraction may apply a generic level-two section terminator before the shared fence-aware firm-heading iterator recognizes valid `## NEW: path` headings. Heading-like text inside fences may also terminate the section prematurely, causing dispatch and dirty-tree scope checks to miss valid paths accepted by the shared grammar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Define section-bound precedence around the shared fence-aware iterator: recognize valid firm headings before generic section termination, and ignore all headings while inside fences. Add fixtures combining level-two headings, fenced heading-like text, and later scope entries.

### FINDING_4: Active replacement extraction is not migrated to terminal `diff_lines` parsing
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: `_extract_file_replacement` remains an active local parser that records the last `diff_lines:` line found anywhere in a candidate block, rather than using the shared terminal contiguous-trailer semantics. Earlier or non-terminal lines can therefore determine the replacement boundary despite the new grammar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Use the shared terminal trailer result when selecting the replacement boundary, reject candidates without a valid terminal `diff_lines`, and add a revise-waterfall fixture with an earlier and a final conflicting `diff_lines:` line.

### FINDING_5: Bootstrap retains an independent `diff_lines` parser
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The bootstrap migration only replaces its optional-size regex while leaving a local whole-line `diff_lines` regex and fence-index scan. This creates a second trailer owner and can let bootstrap handle malformed or non-terminal candidates differently from the shared terminal parser.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Route `diff_lines` location and fenced handling through `plan_grammar` while preserving bootstrap’s provenance-stripping policy, then add a bootstrap regression for conflicting/non-terminal `diff_lines` lines.
