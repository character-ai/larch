# Review Round 4

- Mode: `diff`
- 5 accepted, 9 rejected (9 exonerated)

## Accepted Findings

### FINDING_1: Untracked `parse-bootstrap-routing-envelope` scripts break clean checkout and Step 0
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-missing-file-coverage-output.txt
- **Severity**: important
- **Concern**: Committed `SKILL.md`, structure harness, and bootstrap-invoke harness require `scripts/parse-bootstrap-routing-envelope.sh` and `scripts/parse-bootstrap-routing-envelope.md`, but those files are not in git on the branch (untracked locally). On a clean checkout of `HEAD`, Step 0 sources a missing script after a successful wrapper call; `make test-implement-structure` and `make test-implement-bootstrap-invoke` fail on existence pins; `/implement` session setup cannot complete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: git add and commit scripts/parse-bootstrap-routing-envelope.sh and scripts/parse-bootstrap-routing-envelope.md.
  - From cursor-specialist-testing-output.txt: git add scripts/parse-bootstrap-routing-envelope.sh and scripts/parse-bootstrap-routing-envelope.md and include in the PR
  - From cursor-specialist-security-output.txt: Add commit scripts/parse-bootstrap-routing-envelope.sh and .md (and tests) in the same PR; verify on fresh clone.
  - From cursor-specialist-plan-fidelity-output.txt: Commit scripts/parse-bootstrap-routing-envelope.sh and scripts/parse-bootstrap-routing-envelope.md with the _inv_routing_keys set kept in sync with implement-bootstrap-invoke.sh.
  - From dyn-missing-file-coverage-output.txt: Add and commit `scripts/parse-bootstrap-routing-envelope.sh` and `scripts/parse-bootstrap-routing-envelope.md` (or revert SKILL/harness references and inline the shared parse block in `SKILL.md` as the original plan described); confirm with `git ls-files scripts/parse-bootstrap-routing-envelope.*` and a fresh-clone `make test-implement-structure test-implement-bootstrap-invoke`.


### FINDING_11: Unquoted `IMPLEMENT_TMPDIR` assignment on exit 2
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Unquoted `IMPLEMENT_TMPDIR` assignment from bootstrap stdout on exit 2. Paths with whitespace break tmpdir resolution; stderr redaction may read wrong or missing logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Quote assignment: IMPLEMENT_TMPDIR="$_ib_tmpdir".


### FINDING_4: Missing harness coverage for new exit-2 `STEP_FAILED` arms
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: New exit-2 `STEP_FAILED` arms (`create-branch`, `write-session-env`, `emergency-bypass-log`) lack `run_exit2_case` coverage in `test-implement-bootstrap-invoke.sh`. Regressions in operator stderr or stdout for those paths would not be caught offline until a live bootstrap exit 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Add run_exit2_case for create-branch write-session-env emergency-bypass-log with exact stderr pins and empty stdout.


### FINDING_6: File-first parse and `--preserve-coder` mishandle `coder` / routing precedence
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-envelope-key-completeness-output.txt
- **Severity**: latent
- **Concern**: File-first `bootstrap-routing.env` parsing and unfiltered stdout fallback can apply allowlisted keys (including `coder` / `coder_fallback` and `REPO`) in ways that defeat `--preserve-coder` and session-env authority: non-empty on-disk values can overwrite shell selection; empty `coder=` lines from wrapper capture can clear preserved coders; stale or tampered files can redirect routing without touching `session-env.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-envelope-key-completeness-output.txt: In `_inv_apply_routing_line_if_empty`, skip `coder`/`coder_fallback` when `$_inv_value` is empty (matching file parse), and when `_preserve_coder=true` skip both keys entirely in the stdout-fallback loop; add a small offline harness (or extend `test-implement-bootstrap-invoke.sh`) that sources the parser with `--preserve-coder`, pre-set `coder=codex`, stub `_inv_out` containing `coder=`, and asserts `coder` stays `codex`.


### FINDING_9: `step0_wrapper_fence_status` awk can pass on commented-out wrapper lines
- **Reviewer(s)**: dyn-awk-fence-correctness-output.txt
- **Severity**: important
- **Concern**: `test-implement-structure.sh` `step0_wrapper_fence_status` (and the parallel `step0_plan_structure_status` awk) treat any in-bash line matching `implement-bootstrap-invoke.sh" --mode (initial|resume)` as a call site without requiring an uncommented `_inv_out=$(` prefix. Commented templates plus live `_inv_rc=$?` / `set -e` can satisfy fence exits 20–22 without any wrapper running; with no `_inv_out=$(` pin, `SKILL.md` could drop live invocations and still pass Step 0 structural checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-fence-correctness-output.txt: Tighten both awks so the wrapper match requires an uncommented `_inv_out=$(` prefix (e.g. `$0 ~ /^[[:space:]]*_inv_out=\$\(.+implement-bootstrap-invoke\.sh" --mode (initial|resume)/` and reject `$0 ~ /^[[:space:]]*#/`), and add an explicit pin that `skills/implement/SKILL.md` contains at least two uncommented `_inv_out=$("${CLAUDE_PLUGIN_ROOT}/scripts/implement-bootstrap-invoke.sh"` lines.


