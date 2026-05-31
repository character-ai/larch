### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Bash parity tests skip when bash is unavailable
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Bash parity tests skip when bash is missing, so off-CI pytest on macOS/Windows can pass without parity; drift merges until Ubuntu CI fails. Restrict skip to missing helper scripts only, or fail when `CI=true` and bash is missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: `test-relevant-checks.sh` lacks all-tools-present happy path for Python
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Relevant-checks harness tests Python skip paths but not the happy path when ruff, pylint, pyright, and pytest are on PATH; routing regression when all tools present may go untested. Add a section stubbing tools and asserting both `py-lint` and `py-test` make targets run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: `relevant-checks.sh` skips py-lint/py-test when tools absent
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `py-lint`/`py-test` skipped when tools absent (47–76); Python-only branch can pass relevant-checks locally without pytest/ruff while CI would fail. Fail closed on python changes or require an explicit skip flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: `failed_jobs` silently skips malformed job dicts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `failed_jobs` (362–364) skips malformed job dicts; API shape change could yield an empty failed list with no error. Raise `ShipError` on non-dict job entries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: `proc.run` does not normalize missing binary
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `proc.run` (48–56) does not normalize a missing binary; `FileNotFoundError` escapes instead of structured failure for missing `gh`/`git`. Wrap into `ShipError` or synthetic `CommandResult`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Custom retry predicate can retry successful calls
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Custom predicate in `retry.py` (76–81) can retry when `predicate` is true with `rc == 0`, causing extra attempts and backoff. Ignore transient signature when `rc == 0` or document predicate contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Duplicated parse/refusal classification in `python/agents.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicated parse/refusal classification for `sidecar` vs `output_file` (1148–1159); one path can get a parity fix without the other, breaking `classify_launch_failure` parity. Extract a shared text-classification helper used by both branches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: `run_waterfall` lacks bash skip-tier / `waterfall_iter` semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `run_waterfall` does not implement bash skip-tier / `waterfall_iter` behavior: bash can skip the rotated first tier when the claude launcher is missing; codex `other` failure does not short-circuit the same way in bash. Python may short-circuit at index 0 incorrectly. Filter tiers before `run_waterfall` or add a skip hook matching `run_ci_fix_vendor`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Launcher invocation: cwd-relative paths, executability, and argv shape
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `build_launch_argv` / launcher `proc.run` use cwd-relative `scripts/launch-*.sh` without a `bash` prefix, assuming repo-root cwd and executable bits. From another cwd, without `+x`, or with a consumer repo’s own `scripts/launch-*.sh`, invocation can fail or execute the wrong script (Phase 7 security: attacker-controlled path as operator). Resolve launchers from `CLAUDE_PLUGIN_ROOT` / `RunContext` with absolute paths, prepend `bash` where ship-pr does, and test cwd independence—parity with `SCRIPT_DIR` / ship-pr launcher wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Duplicate stub `Runner` implementations across test modules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicate stub `Runner` implementations in `python/test_git.py` and elsewhere; harness fixes must be duplicated. Share one `RecordingRunner`/`StubRunner` in a colocated test helper module.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

