Structured aggregator output from the supplied reviewer findings (merged by behavioral risk; severity = max across sources).

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

### FINDING_2: Canonical `_inv_routing_keys` list duplicated in four places
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-envelope-key-completeness-output.txt
- **Severity**: latent
- **Concern**: The canonical routing key list is duplicated in `implement-bootstrap-invoke.sh`, `parse-bootstrap-routing-envelope.sh`, `test-implement-structure.sh`, and `test-implement-bootstrap-invoke.sh` with only partial sync checks. Adding a consumer key can update one copy while degraded-tools or ship-pr routing breaks until another copy is noticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-envelope-key-completeness-output.txt: Address the concern above.

### FINDING_3: `_inv_apply_routing_line_if_empty` duplicates allowlist as large `case`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_inv_apply_routing_line_if_empty` duplicates the allowlist as a large `case` statement. A new envelope key requires edits in the allowlist, case arms, export list, and three other files. The `case` should be replaced with allowlist-guarded `printf -v` and an empty check after `_inv_routing_key_allowed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Missing harness coverage for new exit-2 `STEP_FAILED` arms
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: New exit-2 `STEP_FAILED` arms (`create-branch`, `write-session-env`, `emergency-bypass-log`) lack `run_exit2_case` coverage in `test-implement-bootstrap-invoke.sh`. Regressions in operator stderr or stdout for those paths would not be caught offline until a live bootstrap exit 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Add run_exit2_case for create-branch write-session-env emergency-bypass-log with exact stderr pins and empty stdout.

### FINDING_5: No dedicated offline harness for `parse-bootstrap-routing-envelope.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The parse helper has no dedicated behavioral harness. `--preserve-coder`, file-first vs stdout fallback, symlink skip, and stale-file behavior can regress while structure grep pins still pass until a live dirty-tree resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Add fixture-based harness for parse-bootstrap-routing-envelope.sh covering stale file symlink and preserve-coder.

### FINDING_6: File-first parse and `--preserve-coder` mishandle `coder` / routing precedence
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-envelope-key-completeness-output.txt
- **Severity**: latent
- **Concern**: File-first `bootstrap-routing.env` parsing and unfiltered stdout fallback can apply allowlisted keys (including `coder` / `coder_fallback` and `REPO`) in ways that defeat `--preserve-coder` and session-env authority: non-empty on-disk values can overwrite shell selection; empty `coder=` lines from wrapper capture can clear preserved coders; stale or tampered files can redirect routing without touching `session-env.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-envelope-key-completeness-output.txt: In `_inv_apply_routing_line_if_empty`, skip `coder`/`coder_fallback` when `$_inv_value` is empty (matching file parse), and when `_preserve_coder=true` skip both keys entirely in the stdout-fallback loop; add a small offline harness (or extend `test-implement-bootstrap-invoke.sh`) that sources the parser with `--preserve-coder`, pre-set `coder=codex`, stub `_inv_out` containing `coder=`, and asserts `coder` stays `codex`.

### FINDING_7: Success-path routing temp install lacks cleanup on `set -e` failure
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: On the success path in `implement-bootstrap-invoke.sh` (lines 201–205), under `set -euo pipefail`, failure of `cat "$_inv_routing_buf" >"$_inv_routing_tmp"` or `mv -f "$_inv_routing_tmp" "$_inv_routing_file"` aborts before stdout envelope emission and before `rm -f "$_inv_routing_buf"`, leaving temp files and yielding non-zero / partial `_inv_out` capture after bootstrap already completed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Wrap the write in a small cleanup handler (e.g. `trap 'rm -f "$_inv_routing_buf" "$_inv_routing_tmp"' EXIT` scoped to that block, or `mv` then emit stdout from the installed file and `rm -f` both temps in a single `|| { …; exit 1; }` branch) so temp files are always removed and, if `bootstrap-routing.env` was written, stdout still emits the envelope (or a documented non-zero exit after printing it).

### FINDING_8: `mktemp` failure in exit-2 redaction arms can yield exit 1 instead of 2
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: In the `copy-plan` / `gh-issue-view` exit-2 arms, `_ib_redacted_err=$(mktemp …)` runs under `set -e`. If `mktemp` fails, the wrapper exits 1 before the arm’s operator `printf` and before `exit 2`, so callers expecting bootstrap exit 2 (and the SKILL `if [ "$_inv_rc" -eq 2 ]; then exit 2` path) see the wrong code and may miss the canonical stderr message.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Guard `mktemp` (e.g. `if _ib_redacted_err=$(mktemp … 2>/dev/null); then … redact …; rm -f "$_ib_redacted_err"; fi`) and always emit the existing operator string and `exit 2` even when redaction temp allocation fails.

### FINDING_9: `step0_wrapper_fence_status` awk can pass on commented-out wrapper lines
- **Reviewer(s)**: dyn-awk-fence-correctness-output.txt
- **Severity**: important
- **Concern**: `test-implement-structure.sh` `step0_wrapper_fence_status` (and the parallel `step0_plan_structure_status` awk) treat any in-bash line matching `implement-bootstrap-invoke.sh" --mode (initial|resume)` as a call site without requiring an uncommented `_inv_out=$(` prefix. Commented templates plus live `_inv_rc=$?` / `set -e` can satisfy fence exits 20–22 without any wrapper running; with no `_inv_out=$(` pin, `SKILL.md` could drop live invocations and still pass Step 0 structural checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-fence-correctness-output.txt: Tighten both awks so the wrapper match requires an uncommented `_inv_out=$(` prefix (e.g. `$0 ~ /^[[:space:]]*_inv_out=\$\(.+implement-bootstrap-invoke\.sh" --mode (initial|resume)/` and reject `$0 ~ /^[[:space:]]*#/`), and add an explicit pin that `skills/implement/SKILL.md` contains at least two uncommented `_inv_out=$("${CLAUDE_PLUGIN_ROOT}/scripts/implement-bootstrap-invoke.sh"` lines.

### FINDING_10: Harness omits non-regular `bootstrap-routing.env` fallback case
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Contract docs describe non-regular `bootstrap-routing.env` fallback, but the harness only tests symlink. A fifo or other non-regular file could break orchestrator parsing without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: Unquoted `IMPLEMENT_TMPDIR` assignment on exit 2
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Unquoted `IMPLEMENT_TMPDIR` assignment from bootstrap stdout on exit 2. Paths with whitespace break tmpdir resolution; stderr redaction may read wrong or missing logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Quote assignment: IMPLEMENT_TMPDIR="$_ib_tmpdir".

### FINDING_12: Exit-2 `GATE_ERROR` / `PREFLIGHT_ERROR` stderr not redacted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `GATE_ERROR` and `PREFLIGHT_ERROR` lines printed to stderr on exit 2 without `redact-secrets`. If bootstrap KV ever contains tokens, operators see them on the terminal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Run grepped KV lines through redact-secrets.sh and redact-tmpdir-paths.sh like copy-plan/gh-issue-view.

### FINDING_13: Wrapper still uses `_ib_*` locals after SKILL removed `_ib_*` helpers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Contributors searching for `_ib_` may edit the wrong layer after the SKILL removed `_ib_*` helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_14: Three-layer Step 0 split exceeds original plan; needs contract doc
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 0 split into invoke plus parse scripts exceeds the original two-layer plan, increasing cognitive load for Step 0 edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### OOS_1: [OUT_OF_SCOPE] `docs/linting.md` harness shard numbering mismatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test-implement-bootstrap` shard documented as harness-7 vs Makefile harness-15 causes CI shard lookup confusion for maintainers only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] `plugin-root.env` sourcing in dirty-tree recovery
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Malicious `plugin-root.env` in `IMPLEMENT_TMPDIR` could execute arbitrary shell code in the orchestrator during dirty-tree recovery. Pre-existing; harden separately (signing, minimal exports, refuse symlinks).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Heredoc `EOF` delimiter could truncate envelope parse
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A lone `EOF` line in bootstrap stdout could theoretically truncate envelope parse via heredoc delimiter; no known producer emits that line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Non-2 bootstrap rc lacks formatted wrapper operator stderr
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Pre-existing class: exit 1 failures lack formatted Step 0 messages; debugging relies on raw bootstrap output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] `implement-bootstrap.md` missing parse scripts in edit-in-sync block
- **Reviewer(s)**: dyn-missing-file-coverage-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap.md` documents the invoke wrapper but does not list `parse-bootstrap-routing-envelope.*` in its edit-in-sync block (unlike `implement-bootstrap-invoke.md`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-missing-file-coverage-output.txt: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] `test-implement-structure.sh` awk extract diagnosability only
- **Reviewer(s)**: dyn-envelope-key-completeness-output.txt
- **Severity**: nit
- **Concern**: `awk` extraction of `_inv_routing_keys` fails generically on empty extract; dedicated non-empty assertions would improve failure messages only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-envelope-key-completeness-output.txt: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] Harness `mktemp` uses hardcoded `/tmp`
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: nit
- **Concern**: `test-implement-bootstrap-invoke.sh` harness `mktemp` templates use hardcoded `/tmp/…` rather than `${TMPDIR:-/tmp}`; consistent with other offline harnesses, not production Step 0 code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Address the concern above.
