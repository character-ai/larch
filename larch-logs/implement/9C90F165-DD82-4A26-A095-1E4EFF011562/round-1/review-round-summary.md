# Review Round 1

- Mode: `diff`
- 4 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_1: CRLF / line-splitting parity regression in shared KV parsing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Shared `parse_kv` / `kv_value` / `read_kv` now split on `"\n"` with default `cr_strip="none"` instead of `splitlines()` semantics used by deleted helpers. CRLF files, stdout, and session env lines can leave trailing `\r` on values (e.g. `KEY=val\r\n` → `val\r`, `TOOL=codex\r`, `CODEX_BINARY_FOUND=true\r`). That breaks string equality, bootstrap/coder routing, sidecar reads, and env-driven decisions. In `design_lifecycle`, `_read_simple_env` can drop CRLF-parsed values (e.g. `RECOVERY_REQUIRED=true\r\n` treated invalid), so `_postplan_dirty_recovery` may return `False` when recovery is required. Many repointed stdout parsers inherit the same divergence unless each site passes explicit `cr_strip`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use splitlines() in _line_iter or normalize line endings before parsing; add CRLF parity tests
  - From cursor-specialist-correctness-output.txt: Parse with splitlines/cr_strip before the embedded-\r filter, or pass cr_strip=suffix/strip to parse_kv
  - From cursor-specialist-correctness-output.txt: Pass cr_strip=suffix/strip to read_kv or fix line splitting in larch_io
  - From cursor-specialist-correctness-output.txt: Add cr_strip=suffix (or splitlines at read layer) to match prior behavior
  - From cursor-specialist-correctness-output.txt: Add cr_strip=suffix to these read_kv call sites or centralize splitlines semantics
  - From cursor-specialist-correctness-output.txt: Normalize in parse_kv/kv_value or audit all stdout parsers with explicit cr_strip and tests
  - From cursor-specialist-edge-cases-output.txt: Use cr_strip="suffix" on file readers that replaced splitlines() loops, or split lines like splitlines() inside read_kv/kv_value
  - From codex-specialist-edge-cases-output.txt: Use splitlines for parse_kv default line iteration, or only preserve raw CRs on explicit reject_cr/raw-read paths.
  - From codex-specialist-testing-output.txt: Restore splitlines/universal-newline parity or pass explicit cr_strip at each affected repoint, with CRLF parity tests.


### FINDING_3: `_read_kv_raw` missing-file guard removed
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: blocking
- **Concern**: `_read_kv_raw` no longer returns `{}` for missing files. An implement tmpdir with `ship-pr-state.sh` but no `finalize-state.sh` now crashes in `restore_finalize_state_main` instead of writing defaults.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Restore the missing-file guard before _read_kv_file_text.


### FINDING_4: `atomic_write` unlinks refused symlink temp
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `atomic_write` refuses a symlink temp but then unlinks it in generic cleanup. `session_env._atomic_write` with `session-env.sh.tmp` as a symlink raises once, deletes the symlink, and a retry can proceed instead of continuing to refuse the unsafe temp path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Skip cleanup for symlink-refusal paths or only unlink temp paths that are not symlinks.


### FINDING_10: `plan_quality` `atomic_write` predictable temp regression (collision and symlink risk)
- **Reviewer(s)**: codex-specialist-testing-output.txt, dyn-dyn-atomic-safety-output.txt
- **Severity**: blocking
- **Concern**: `plan_quality._atomic_write` now calls bare `larch_io.atomic_write(path, text)`, which uses a predictable sibling temp (`<dest.name>.tmp`) via `write_text` without `O_EXCL` or `nofollow`. The pre-refactor helper used `tempfile.mkstemp(prefix=f".{path.name}.", …)`, so temp names were unpredictable and not attacker-placeable. Concurrent writes or stale sibling temps can collide where the old unique temp path did not. For plan-quality artifacts (plans, revise prompts, `.env` sidecars), a local attacker who can create `<dest>.tmp` as a symlink in the same directory can redirect the write before `replace`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Pass prefix=f".{path.name}." to larch_io.atomic_write here or make the shared default mkstemp for callers without temp_name, with a temp-collision parity test.
  - From dyn-dyn-atomic-safety-output.txt: restore mkstemp-style behavior, e.g. `larch_io.atomic_write(path, text, prefix=f".{path.name}.")`, or pass an explicit `temp_name` plus `exclusive=True` / `nofollow=True` if a fixed sibling temp is required.


