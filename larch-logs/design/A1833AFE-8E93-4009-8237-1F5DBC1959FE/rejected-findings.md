### [Plan Review] FINDING_1

### FINDING_1: Accept inline Markdown fence-state guards
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The proposed Markdown-heading lint is too narrowly specified if it requires importing or defining `_balanced_fence_line_indices`. Existing compliant parsers gate heading matches with inline fence-state tracking in the same `splitlines()` loop, so a helper-centric rule would produce false positives against production code such as `python/larch/review/voting.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define compliance as same-function data flow: any splitlines iteration that matches a heading regex must skip fenced indices via a helper call, an index-not-in-fenced-lines guard, or an equivalent inline in_fence toggle updated on fence markers before the heading match.
  - From Cursor-Pragmatic: Extend the compliance rule to accept same-function fence-state guards that skip heading matches inside fenced regions, including inline toggles and index-set helpers. Add a positive test fixture for the voting.py pattern so implementers do not require _balanced_fence_line_indices at every call site.


### [Plan Review] FINDING_2

### FINDING_2: Exempt trusted operator oversize overrides from self-disarm detection
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The self-disarmable-gate lint must distinguish author-controlled plan metadata from the authority-verified operator oversize override. `_size_trigger_assessment` receives `oversize_override` from `_trusted_oversize_override` in production, so identifier- or field-based matching could incorrectly flag the legitimate operator-authorized suppression of `SIZE_TRIGGER_FIRED`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Limit disarm detection to author-controlled OptionalMetadata field reads (meta.diff_added, meta.mechanical_churn, etc.) in trigger-suppression control flow, and explicitly exempt override_suppressed when its oversize_override argument is supplied from _trusted_oversize_override rather than parsed plan metadata.
  - From Cursor-Pragmatic: State the lint rule explicitly: flag suppression only when plan-meta fields such as meta.oversize_override feed the trigger decision without a trusted-authority check. Treat override_suppressed driven by _trusted_oversize_override or equivalent sidecar-verified input as compliant operator override, not model self-disarm.


### [Plan Review] FINDING_3

### FINDING_3: Specify unreachable-branch baseline identity
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The unreachable-branch baseline identity is underspecified. Without exact rules for normalized conditions, returned-value equivalence, and occurrence counting, unrelated edits may churn or duplicate baseline rows and undermine shrink-only enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin baseline rows to the established occurrence-counter pattern plus an AST-unparsed normalized condition string and a separate normalized return-expression key; document the exact tuple in docs/linting.md the same way other structural lints document baseline identity.


### [Plan Review] FINDING_4

### FINDING_4: Provide mechanical backing for I-Commit-1
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The plan adds I-Commit-1 while explicitly omitting its required mechanical backing. The committed run-log path could continue writing tmpdir pointers even though the repository claims that a commit-time scan rejects them, leaving the invariant unenforced and its audit guarantee false.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Implement the commit-time staged-log scan and extend the existing run-log flush/redaction path to embed voted finding bodies, or do not add I-Commit-1 until that backing ships.


