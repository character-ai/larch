### FINDING_1: approval-gates Discuss-more re-prompt vs Shape_2 three-option Gate_A
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: After “Discuss more,” the discussion sub-round still tells the operator to re-prompt with a two-option AskUserQuestion, which conflicts with Shape 2’s three-option Gate A on post-plan re-entry and can drop “Show latest design proposal” from the loop—breaking the intended UX contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Make re-prompt wording match Shape 1 vs Shape 2 (same shape as entry).
  - From cursor-specialist-correctness-output.txt: Reword to two-option vs three-option re-prompt keyed on first-time vs Gate B/C re-entry.
  - From cursor-specialist-testing-output.txt: Qualify the re-prompt instruction: two options on first-time Gate A; three options when operating under Shape 2 (Gate B(c)/Gate C(b) re-entry)
  - From cursor-specialist-edge-cases-output.txt: Clarify re-prompt uses three options when re-entered post-plan (Shape 2) vs two on first-time (Shape 1).
  - From cursor-specialist-plan-fidelity-output.txt: Branch the sentence by Shape 1 vs Shape 2 or replace with shape-neutral wording tied to the prior prompt


### FINDING_11: design SKILL Bash uses lowercase mental flags vs prelude uppercase exports after sourcing current-design-env
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Bash passes `--codex-present` / `--cursor-present` using unset mental-flag names `codex_available` / `cursor_available` while the prelude only exports `CODEX_*` uppercase vars; after sourcing `current-design-env.sh`, lowercase names expand empty and `dispatch-with-waterfall.sh` may reject empty with exit 2, aborting Step 3 plan-review dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use sourced exports (e.g. CODEX_AVAILABLE/CURSOR_AVAILABLE if semantically correct) or export lowercase aliases from write-design-current-env.sh and document them.


### FINDING_12: docs/linting.md implies live /design calls session-entry-gate
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: A `test-session-entry-gate` row still claims `/design` uses the gate while live `/design` no longer calls `session-entry-gate.sh`, misleading operators about who invokes the gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Reword to /implement-only (and harness-only nested cases) without implying live /design calls it


### FINDING_2: design SKILL Step_0 separate Bash blocks and bare DESIGN_TMPDIR expansion
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Step 0 splits `session-setup`, `write-design-current-env`, and `write-run-params` across separate Bash invocations while expanding `DESIGN_TMPDIR` / `SESSION_ID` / related vars in fresh subshells without a prelude; a literal paste can collapse paths to `/source-env.sh` or `/run-params.json` when `DESIGN_TMPDIR` is unset, repeating the same failure class as the reported `/design --trivial` bug and undermining env persistence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Combine with session-setup in one shell, or require literal substituted SESSION_TMPDIR for those invocations only.
  - From cursor-specialist-correctness-output.txt: Chain session-setup parse + writer in one Bash block; prepend prelude (or merge) before write-run-params so DESIGN_TMPDIR is defined in-shell.
  - From cursor-specialist-edge-cases-output.txt: Merge setup+writer into one Bash call or mandate literal absolute paths for the writer argv in Step 0 prose.
  - From cursor-specialist-plan-fidelity-output.txt: Merge session-setup + writer in one Bash block and/or add prelude to post-writer Step 0 fences


### FINDING_3: test harness fixed /tmp stderr paths for negative tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Concern**: Negative tests use fixed `/tmp/...` stderr paths, risking parallel harness collision, flaky overwrites, misleading results on multi-user hosts (including symlink attacks on predictable paths).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use $TMPROOT or mktemp for diagnostic paths.
  - From cursor-specialist-testing-output.txt: Redirect case-5 stderr into TMPROOT-scoped temp files and grep those
  - From cursor-specialist-security-output.txt: Redirect stderr into $TMPROOT with unique filenames per case.


### FINDING_4: write-design-current-env.md symlink wording vs file atomicity
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Documentation describes symlink update as “atomic” in a way that parallels the temp+`mv` file write, which overstates symlink replacement semantics and can mislead readers about failure modes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Soften symlink wording or split atomicity claims per artifact type.
  - From cursor-specialist-edge-cases-output.txt: Rephrase to describe symlink replacement without claiming same atomicity as the file body write.


### FINDING_6: agent-lint exclusion / allowlist for new design harness scripts
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The new design harness may not be covered by existing `agent-lint.toml` Makefile-only exclusion patterns, so rules like G004 / dead-script detection could fail CI until paths are allowlisted consistently with other `skills/design/scripts/test-*` peers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add skills/design/scripts/test-write-design-current-env.sh and skills/design/scripts/test-write-design-current-env.md next to the existing test-design-driver..test-finalize-plan entries with matching comments


### FINDING_7: SECURITY.md Trust Model omits stable-path sourced session-env boundary
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `SECURITY.md` does not document the new `/design` stable-path sourced `session-env` boundary while `AGENTS.md` documents symlink single-runner semantics; auditors/operators may not realize Bash steps execute generated shell from `~/.cache/larch/sessions/current-design-env.sh`, conflicting with the repo norm to document security-relevant behavior in `SECURITY.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add a Trust Model subsection describing write-design-current-env.sh as sole writer, %q-quoted exports, symlink refresh, single-/design invariant, and same-user trust assumptions.


