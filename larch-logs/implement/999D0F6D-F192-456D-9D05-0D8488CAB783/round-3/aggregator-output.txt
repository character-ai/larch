### FINDING_1: Rule 2 fixtures suppress the violations they are meant to test
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Cases 16-17 in `scripts/test-lint-awk-multibyte-regex.sh` place `lint-awk-multibyte-regex ok` pragmas inside fixture awk-body lines that are expected to violate Rule 2, so the lint can exit 0 or fail to exercise the intended pipeline-close / callsite coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_2: Rule 2 `sub(` detection false-positives on `substr(`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `regex_callsite` matches bare `sub(`, which also matches `substr(`, so non-ASCII comments plus `awk substr()` can be incorrectly reported as `awk-body-nonascii-regex`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Inline awk scanner is large and duplicates nearby lint logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The embedded awk scanner in `scripts/lint-awk-multibyte-regex.sh` duplicates `-v` skipping and related enumeration logic, making future rule changes more regression-prone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Test harness uses bare `grep` despite doc claiming `command grep`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-lint-awk-multibyte-regex.md` says the harness uses `command grep`, but the shell harness uses bare `grep`, which can terminate Claude Code Bash blocks on non-zero exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Changelog categorizes additive lint behavior under Fixed
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The changelog places the new lint and related ship-pr behavior under `### Fixed`, which can misclassify new enforcement/capability surface as bugfix-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: `ship-pr.sh` HEAD comparison can be defeated by run-log commits
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The HEAD-non-advance check runs after run-log refresh may commit `larch-logs`, so a vendor no-op plus log-only commit can advance HEAD and avoid `first-fixer-non-health`, causing retries instead of autonomous CI-fix routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: Rule 2 does not scan double-quoted awk bodies
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The lint tracks single-quoted awk program bodies but misses double-quoted awk bodies containing non-ASCII dynamic regex strings, allowing the Ubuntu CI failure class to pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Default ship-pr test launcher stub always commits
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The default `make_repo` launcher stub in `scripts/test-ship-pr.sh` always commits, so future tests may unintentionally model vendor HEAD advancement instead of vendor exit 0 with no commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Lint contract example points readers toward POSIX-class root cause
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-awk-multibyte-regex.md` uses a POSIX-class example, which may send operators toward `[[:...:]]` fixes instead of the multibyte literal root cause for this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Feature description may imply POSIX lint coverage outside branch scope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The feature description can be read as broader POSIX lint coverage even though the plan scope was multibyte-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Missing ship-pr test for lint-fix-loop-only HEAD advance
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-ship-pr.sh` lacks coverage for vendor no-op plus committing lint-fix-loop behavior, where production should return success rather than misclassify as `first-fixer-non-health`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Missing ship-pr test for stage-and-push failure classification
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no test ensuring a `git-push` / stage-and-push failure after a no-commit vendor does not set `first-fixer-non-health`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Multi-callsite Rule 2 test only asserts the first violation line
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Case 17 checks only the first reported violation, so regressions in later `gsub` / `sub` / `split` callsite detection could be missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] No mawk/POSIX-class dynamic-regex lint or smoke test
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The branch does not cover the original POSIX-class dynamic `match()` bug class with a lint or smoke test; reviewers identified this as follow-up or parallel-PR scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Lint green may depend on parallel readability-preamble fix
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `make lint` / pre-commit may still fail on main patterns until the parallel `lint-readability-preamble.sh` em-dash fix lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Lint violation output can echo source-line secrets
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-awk-multibyte-regex.sh` prints up to 120 bytes of offending source lines, so a literal secret embedded in an awk `-v` value could appear in CI or pre-commit output; reviewer marked this as same class as other line-printing lints.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Sibling lint path construction lacks shared hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Unchanged sibling lint `scripts/lint-bare-grep-probe.sh` builds paths as `$ROOT/$rel` without a realpath/prefix guard; reviewer scoped this to shared hardening outside this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: HEAD-only no-commit bail may ignore untracked vendor work
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If a vendor creates only untracked fix files and `_stage_and_push` commits nothing, the current HEAD-only check can escalate as `first-fixer-non-health` even though the vendor made edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: Rule 2 is not applied to trailing continuation at EOF
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The END block applies only Rule 1 to a pending trailing continuation, so a non-ASCII regex token split across a final backslash continuation at EOF can evade Rule 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: Tier-order tests diverge from the plan’s sentinel filename
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The tier-order happy-path tests touch `README.md` instead of the plan’s literal `sentinel-fix.txt`, reducing traceability even if behavior is equivalent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
