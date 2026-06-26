### FINDING_1: validator-failure.md NEW subsection omits column-0 Consumer/Contract/When-to-load header triplet
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The NEW `validator-failure.md` subsection documents Contract and When-to-load prose but does not pin line-anchored `**Consumer**:`, `**Contract**:`, and `**When to load**:` each at column 0 (not bullet-prefixed), unlike sibling NEW subsections (`step2b5-rc-handling.md`, `step2b-drafter-failsafe.md`, `sentinel-host-table.md`). An implementer can ship prose-only or bullet-prefixed headers and fail `make test-references-headers` (`^\*\*Consumer\*\*:` at line start).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror the other NEW subsections: require **Consumer**:, **Contract**:, and **When to load**: each at column 0 (not bullet-prefixed) before the moved body in validator-failure.md.
  - From Cursor-Innovation: Mirror the `step2b5-rc-handling.md` NEW subsection header-triplet block in `validator-failure.md`, requiring line-anchored column-0 `**Consumer**:`, `**Contract**:`, and `**When to load**:` before the moved body.
  - From Cursor-Pragmatic: Add the same column-0 triplet spec used in the other NEW reference subsections (`**Consumer**:`, `**Contract**:`, `**When to load**:` each at column 0, not bullet-prefixed) before the body-move bullets in `### NEW: skills/design/references/validator-failure.md`.
  - From Cursor-Requirements: Mirror the other NEW subsections: add Create with line-anchored header triplet at column 0 (**Consumer**:, **Contract**:, **When to load**:) before the move-inventory bullets


### FINDING_4: Override-after-defects misclassified as direct-entry path skipping items 1-2
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: Live retained Step 2b.5 runs `design-step2b5.sh` for Override-after-defects and Gate B after validator Override (`SKILL.md:507-515`). The plan lists Override-after-defects among paths where items 1-2 did not run (direct-entry with sidecar KV bind only) while also classifying it as a full-procedure retained caller. An implementer can skip the launcher fence, treat stale `.design-postplan-emit-result.env` as authoritative, and run branches 4-7 with wrong or empty metrics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Remove Override-after-defects from the direct-entry list (lines 20-21, failure-mode bullets at 169/184, and `step2b5-rc-handaling.md` When-to-load line 94). Keep it only on the retained full-procedure path: items 1-2 inline, MANDATORY READ immediately before item 3.
  - From Cursor-Requirements: Remove Override-after-defects from all items-1-2-skipped / direct-entry lists and from settle-rc-dispatch routing prose; keep it only under retained callers with MANDATORY READ immediately before item 3 (plan line 22)

