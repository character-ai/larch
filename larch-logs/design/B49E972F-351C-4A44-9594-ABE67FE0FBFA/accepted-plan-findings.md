### FINDING_1: Review Step 0 Retain list omits SESSION_TMPDIR and reviewer presence keys
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The `skills/review/SKILL.md` UPDATED Step 0 **Retain** parse/bind enumeration still lists only token-session fields and `LARCH_TIMING_LEDGER`, omitting `SESSION_TMPDIR` and the four reviewer stdout keys (`CODEX_BINARY_FOUND`, `CURSOR_BINARY_FOUND`, `CODEX_PRESENT`, `CURSOR_PRESENT`) that Testing step 3, Failure modes, and current Step 0 require before `agent degraded-tools-gate`. A section-scoped implementer can edit only the Retain bullets, drop tmpdir or presence parsing, and leave gate prose intact, breaking `REVIEW_TMPDIR=$SESSION_TMPDIR` binding and degraded-tools routing. Incomplete fix for prior accepted review Retain findings (rounds 3–4).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Expand the Review Step 0 Retain parse/bind enumeration to match Testing step 3: SESSION_TMPDIR, all four reviewer keys, token-session fields, and LARCH_TIMING_LEDGER. Keep the shared session-setup-output.md citation as additive prose only.
  - From Cursor-Innovation: Expand the Review Step 0 Retain enumeration to match Testing step 3: SESSION_TMPDIR, all four reviewer keys, token-session fields, and LARCH_TIMING_LEDGER, with the same explicit parse/bind wording used for design and research.
  - From Cursor-Pragmatic: Expand the Retain parse/bind enumeration to match Testing step 3: `SESSION_TMPDIR`, `CODEX_BINARY_FOUND`, `CURSOR_BINARY_FOUND`, `CODEX_PRESENT`, `CURSOR_PRESENT`, token-session fields, and `LARCH_TIMING_LEDGER`.
  - From Codex-Pragmatic: Expand the retained parse list to include `SESSION_TMPDIR`, `CODEX_BINARY_FOUND`, `CURSOR_BINARY_FOUND`, `CODEX_PRESENT`, and `CURSOR_PRESENT` alongside the token-session fields and timing ledger.
  - From Cursor-Requirements: Expand the Retain parse/bind enumeration to match Testing step 3: `SESSION_TMPDIR`, all four reviewer keys, token-session fields, and `LARCH_TIMING_LEDGER`, with the same explicit-list pattern used for design and research.


### FINDING_2: Two `--run-id` consumers lack explicit replace-with-cite UPDATED steps
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: `skills/issue/SKILL.md` (line 45) and `skills/set-up-forked-open-source-repo/SKILL.md` (line 70) still ship the shared long `--run-id` phrase, but their UPDATED sections only preserve behavior or cite flag-doc scope without instructing replacement with `skills/shared/run-id-flag.md`. Approach items 1–3 and Testing grep #1 require zero hits for that phrase across all eight current SKILL.md consumers; six other skills already have explicit replace steps. A section-scoped implementer can satisfy the sparse UPDATED blocks and leave two of eight n-gram hits in place, failing grep acceptance and leaving the targeted `--run-id` dedup incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit replace-with-cite steps to both UPDATED sections: replace the long inline --run-id flag prose with a short cite of skills/shared/run-id-flag.md. Keep issue parsing behavior and set-up-forked Step 52 strip --run-id before coordinator invocation unchanged.
  - From Codex-Arch: Add the replacement instruction to `### UPDATED: skills/issue/SKILL.md`
  - From Codex-Arch: Add the replacement instruction to `### UPDATED: skills/set-up-forked-open-source-repo/SKILL.md`
  - From Cursor-Innovation: A section-scoped implementer can leave both files unchanged, grep acceptance fails, and the targeted --run-id duplication remains. Add explicit replace-with-cite steps to both UPDATED sections, mirroring cleanup and alias: replace the long inline --run-id prose with a short cite of skills/shared/run-id-flag.md while preserving issue parsing or set-up-forked strip-before-coordinator behavior.
  - From Cursor-Pragmatic: Add explicit replace instructions mirroring `cleanup`/`alias`: replace the long inline `--run-id` prose with a short cite of `skills/shared/run-id-flag.md`, keeping issue strip behavior and fork `--run-id` stripping unchanged.
  - From Codex-Pragmatic: Add explicit replacement instructions in both UPDATED sections, and keep only the fork / issue behavior notes local.
  - From Cursor-Requirements: Add an explicit step: replace the flags-table `--run-id` line with a short cite of `skills/shared/run-id-flag.md`; keep all parsing, dedup, dependency, and redaction behavior unchanged.
  - From Cursor-Requirements: Add an explicit step: replace the flags `--run-id` line with a short cite of `skills/shared/run-id-flag.md`; retain the existing Step 1 strip-`--run-id` instruction and all fork remote-configuration behavior.


