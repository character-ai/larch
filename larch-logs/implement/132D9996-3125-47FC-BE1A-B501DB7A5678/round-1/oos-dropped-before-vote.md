### OOS_1: [OUT_OF_SCOPE] `docs/linting.md:270` usage table not updated for no-path rg checks
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The `make test-lint-bare-grep-probe` usage row still describes the old #3104 bare-`grep` matrix and does not mention no-path `rg`/`ripgrep`, `< /dev/null`, argv truncation, or brace-group cases added in this branch. The linter table row was updated; line 270 was not. Doc drift only; harness and CI behavior are correct and tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Update the usage-table description to mention no-path rg/ripgrep rejection

### OOS_2: [OUT_OF_SCOPE] `grep -l` parser quirk not exercised in repo
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `option_takes_value` treats `grep -l` as consuming the next token as an option argument. A fence line like `command grep -l PATTERN file.txt` would be rejected even though real `grep -l` takes the pattern as the next positional arg and `file.txt` as the path. No in-scope markdown uses this shape today. Latent parser quirk aligned with the plan's conservative flag list; not exercised in the repo.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] runtime ad-hoc probes remain unconstrained
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The lint hardens committed skill/orchestrator fences, but runtime ad-hoc probes (the original #5740 incident) are still unconstrained. That matches the plan's explicit non-goal (no Step 18 reaping). Pre-existing scope boundary, not a regression from this diff.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] piped consumer forms intentionally allowed
- **Reviewer(s)**: dyn-dyn-awk-parser
- **Severity**: latent
- **Concern**: Piped consumer forms such as `cat file.txt | rg PATTERN` remain intentionally allowed because the first command word is not grep-family; that matches the documented pipeline carve-out in `scripts/lint-bare-grep-probe.md`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] accepted tokenizer shape limitations
- **Reviewer(s)**: dyn-dyn-awk-parser
- **Severity**: latent
- **Concern**: The line-based tokenizer does not model `$()`, backslash-continued lines, or here-doc bodies; false results on those shapes are an accepted limitation of the shape-based linter, consistent with `scripts/lint-bare-grep-probe.md` §Limitations.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] omitted rare flags acceptable trade-off
- **Reviewer(s)**: dyn-dyn-awk-parser
- **Severity**: latent
- **Concern**: Omitted rare grep/ripgrep flags can still cause false allows or false rejects; the plan already lists that as an acceptable trade-off for a conservative, reviewable pragma model rather than a full shell parser.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] `BASH_AUTHORING.md` piped-safe paragraph names only `grep`
- **Reviewer(s)**: dyn-dyn-contract-sync
- **Severity**: nit
- **Concern**: The piped-safe paragraph names only `grep` (`printf X | grep Y`, `cat file | grep Y`). `scripts/lint-bare-grep-probe.md:52-53` and `docs/linting.md:25` also allow `cmd | rg` / `cmd | ripgrep`. Worth a one-line extension for parity; low materiality today because the Background stdin section already covers producer `rg` / `ripgrep`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] `docs/linting.md:25` placeholder pipe wording
- **Reviewer(s)**: dyn-dyn-contract-sync
- **Severity**: nit
- **Concern**: The table cell uses placeholder wording `cmd PIPE rg` / `cmd PIPE grep` instead of shell `|`. Meaning is clear; normalizing to `cmd | rg` would read better.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] inline awk parser maintenance cost
- **Reviewer(s)**: dyn-dyn-contract-sync
- **Severity**: nit
- **Concern**: The no-path rule adds a large inline awk parser to a residual Bash linter. That matches the plan and existing lint style, but future flag drift (`grep -l`-style) will keep needing manual list updates; a noted maintenance cost, not a merge blocker for this scope.
- **Suggested revisions (informational for voters; coder decides)**:

