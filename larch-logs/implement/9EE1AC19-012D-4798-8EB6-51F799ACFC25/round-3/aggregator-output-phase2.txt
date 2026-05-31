Structured aggregator output from the supplied reviewer findings (merged by behavioral risk; severity = max across sources).

### FINDING_1: Duplicate MD anchor-insertion logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_write_md_entry` duplicates anchor-insertion logic from `_insert_md_at_anchor`. Fixing Unreleased/SemVer anchor behavior in one path leaves the other wrong; `write_changelog_entry` and commit paths can diverge silently. Reuse `_insert_md_at_anchor` or extract one shared anchor helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Duplicate `_redact_outbound` across Phase 2 modules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicate `_redact_outbound` in `python/changelog.py` and `python/version_bump.py`. Redaction policy changes require two edits; risk of inconsistent error strings. Prefer a single helper in `redact.py` imported by both modules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Duplicated drop-commit walk/reset/rebase blocks
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Near-identical drop-commit walk/reset/rebase blocks in `changelog.py` and `version_bump.py`. Bugfixes in drop mechanics (e.g. rebase abort, depth walk) must be duplicated; one module can drift from bash parity. Shared drop walker in `bump_worktree` with pluggable subject/file guards is suggested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Duplicated test runner doubles
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicated `ProcRunner` and `StubRunner` test doubles in `test_version_bump.py` and `test_changelog.py`. Runner behavior changes need parallel edits in two large test files. Extract a shared fixtures module imported by both.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Oversized single `changelog.py` module
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Single very large changelog module (MD+RST+git). Harder review and higher risk of subtle RST vs MD regressions as Phase 3+ adds behavior. Defer split until needed; plan a facade plus format-specific modules before Phase 7 cutover if growth continues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Nested closures in `apply_bump` retry loop
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `apply_bump` uses nested closures for backup/rollback inside the retry loop. Same-version-race fixes are harder to reason about and unit-test in isolation. Lift helpers to module-level functions with explicit parameters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Frontmatter delimiter strip vs bash column-0 `---`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `_extract_frontmatter` treats the opening delimiter as `lines[0].strip() == "---"` and closes on any line with `line.strip() == "---"`. Bash `classify-bump.sh` requires `^---$` at column 0 (no surrounding whitespace). A skill/agent file whose first line is ` --- ` or trailing-space `--- ` can be classified differently (flag/`name:` evidence) between Python and bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_8: `bump_worktree` imported but not committed on branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Committed code imports `bump_worktree` but `python/bump_worktree.py` is not on the branch (untracked only / not in HEAD or branch diff). Clean checkout / CI: `make py-test` / pytest fails at import with `ModuleNotFoundError: bump_worktree` before Phase 2 tests run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: `classify_bump` fails hard on `git show` errors
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `classify_bump` raises `ShipError` when `git show` fails for a modified public-surface file; bash `classify-bump.sh` continues with empty content. Example: `git show base:skills/foo/SKILL.md` fails while the path is listed in name-status — Python crashes classify; bash may still return PATCH/MINOR/MAJOR from other evidence or default PATCH. Match bash fail-soft (skip file) or document/test fail-loud policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: `sorted_changed_files` UTF-8 byte sort vs bash `LC_ALL=C`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `sorted_changed_files` uses UTF-8 byte sort, not `LC_ALL=C` sort used by `drop-bump-commit.sh` guard 4. Custom `LARCH_BUMP_FILES` paths with non-ASCII characters can sort differently; `drop_bump_commit` guard 4 may disagree with bash on whether to drop. Use locale-aware C-sort parity or restrict documented bump file paths to ASCII.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Weak classify idempotency parity coverage (cases 3–4)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test_parity_classify_idempotency_cases` test3/test4 omit harness fixtures; only assert Python equals bash on a bare repo. `larch-logs` transparent NONE and CHANGELOG-over-feature PATCH edges are never asserted; bash and Python can agree on the wrong PATCH. Port `test-classify-bump.sh` cases 3–4 fixtures; assert expected `BUMP_TYPE`, not only bash==py.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Missing bash-parity test for RST `auto_resolve`
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: No bash-parity test for RST `auto_resolve` vs `auto-resolve-changelog.sh` (plan acceptance). Only a private `_auto_resolve_rst` unit test exists. RST merge can diverge from awk/bash while CI passes; Phase 3 RST conflict resolution risk. Add skipif-guarded subprocess parity with identical `:2:`/`:3:` RST stages (or twin-repo fixture against `scripts/auto-resolve-changelog.sh`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: `test_parity_auto_resolve_subprocess` can skip without exercising parity
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test_parity_auto_resolve_subprocess` skips when merge or bash resolve fails. CI can stay green with zero subprocess parity runs if the fixture stops conflicting. Use a deterministic conflict fixture or fail when the parity path is not exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Missing test for drop_bump exact file-set guard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Missing unit/integration test for `drop_bump` exact file-set guard (extra file refuses drop). Subset bug could drop bump commits that bash would refuse. Add test: bump changes `plugin.json` plus extra file; expect `dropped=False`; optional bash KV parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: `git.add` / `git.commit` lack direct StubRunner argv tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `git.add` and `git.commit` lack direct StubRunner argv tests per plan. Argv regression in commit/`only=` path can break bump/changelog without failing `test_git`. Add minimal `test_git` cases for `add`, `commit -m`, and `only` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: Harness path loaded but `test-classify-bump.sh` not run
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Harness path is loaded but `test-classify-bump.sh` is never run. Misleading signal that the offline harness backs pytest parametrization. Run the harness, remove the unused path, or implement fixtures inline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: `implement_tmpdir` sentinel touch not confined to session tmp
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `implement_tmpdir` sentinel touch is not confined to a trusted session directory. At Phase 7, poisoned or mis-set `IMPLEMENT_TMPDIR` can create `.bump-version-armed` outside the intended session tmp tree. Resolve `implement_tmpdir` and reject paths outside the session tmp root before touch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: Error/stall strings bypass `_redact_outbound`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ShipError`/stalled messages bypass `redact.py` for git paths and branch names. Uncaught errors or stall logs in CI/run logs may emit sensitive branch names or path fragments. Route all outbound error/stall strings through `_redact_outbound` before raise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] `git.py` inherits broad `os.environ`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Git helpers still inherit most of `os.environ`. Malicious env could point git at alternate object stores (pre-existing subprocess model). Extend `_git_subprocess_env` allowlist/denylist if hardening the git trust boundary repo-wide.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Parity tests use `bash -c` with constructed scripts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Parity tests invoke `bash -c` with constructed scripts. No production exposure; scripts use fixed repo paths. No change required unless tests ever embed untrusted input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_21: `commit_changelog` lacks rollback on git failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `commit_changelog` writes the file then fails without rollback on `git add`/`commit` errors. Failed commit leaves dirty CHANGELOG; retry may confuse the Phase 7 driver. Restore from HEAD on failure or document caller reset contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: `apply_bump` `rev_parse` failure after successful commit
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `apply_bump` uses `rev_parse` after commit; `ShipError` escapes on rev-parse failure. Bump commit may have landed but caller gets an exception instead of `ApplyResult`. Use `try_rev_parse`; return `applied=True` with empty SHA or `applied=False` with error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: `rebase --abort` result ignored after failed drop
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `rebase --abort` result ignored after failed `drop` `rebase_onto`. Repo may stay in rebase state after failed drop. Check abort return code; return explicit recovery error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_24: No stderr logging on `apply_bump` origin/main race retries
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: No stderr logging on `apply_bump` `origin/main` race retries. Operators lack retry visibility during version races. Mirror `apply-bump.sh` `larch_err` retry lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_25: Untested RST blank/absent extract cases
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan requires extract blank/absent cases for Markdown and RST; RST blank extract is untested. Blank RST version sections could return wrong body without test failure. Add `test_rst_extract_blank_returns_none` (and optional absent-version case).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_26: Missing bash parity for successful plugin.json-only bump drop
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `drop-bump-commit.sh` lacks bash parity for successful default plugin.json-only drop. Guard-4 or drop mechanics could drift on the common rebase+re-bump path. Add twin-repo parity test for successful plugin.json-only bump drop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_27: `_rst_merge_first_index` diverges from bash `rst_merge_fh`
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `_rst_merge_first_index` only skips a leading `=`-underlined title when `lines[fh1] == "Changelog"` or that title is not in `_rst_release_section_indices`. Bash `auto-resolve-changelog.sh` `rst_merge_fh` skips any first section whose underline is all `=` (`ul ~ /^=+$/`), with no title check. A semver release block at the top with an `=` underline can be treated as the merge/insert anchor in Python while bash skips it — `auto_resolve`, `write_changelog_entry`, `drop_version_section`, and `extract_version_body` can diverge on the same file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_28: `_insert_rst_after` always appends trailing newline
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `_insert_rst_after` always appends `"\n"` while `_write_md_entry`, `_drop_md_section`, and `_drop_rst_section` preserve whether the input ended with a newline. RST insert can add a newline to a previously newline-free file and change byte-level diffs on round-trip edit/drop vs Markdown/awk behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] `sorted_changed_files` / `LC_ALL=C` attestation (parity OK)
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: `files.sort(key=lambda s: s.encode("utf-8"))` in `python/bump_worktree.py:38-39` matches byte-order `sort` for UTF-8 paths; `test_sorted_changed_files_c_locale_order` covers non-ASCII ordering. Default drop guard string equality aligns with `drop-bump-commit.sh` / `drop-changelog-commit.sh`. (Contrasts with in-scope FINDING_10 on custom `LARCH_BUMP_FILES` / documented ASCII-only gap.)
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] `_today_iso()` matches shell `date`
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: `datetime.now().astimezone().date().isoformat()` matches `date +%Y-%m-%d` under the same `TZ` as the shell (format `YYYY-MM-DD`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Idempotency helpers match bash
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: `_idempotency_transparent` / `_idempotency_ref` in `version_bump.py` match `idempotency_commit_is_transparent` (subject prefixes, `CHANGELOG.md`-only vs `larch-logs/**`, empty diff-tree, depth cap 3).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] KV booleans / Phase 7 `emit_kv` adapter
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: This phase returns frozen dataclass `bool`s, not stdout `APPLIED=true` / `COMMITTED=true` / `DROPPED=true`; parity tests normalize with `str(...).lower()`. Phase 7 needs an explicit `emit_kv` adapter (`true`/`false`, not `True`/`False`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] `apply_bump` unmerged exit mapping
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: `apply_bump` returns `ApplyResult(applied=False, …)` rather than exit 4; matches the plan (exit mapping is driver-side). ERROR text is shorter than `apply-bump.sh` (no `git merge/rebase --continue` hints); parity tests only compare `APPLIED`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] `check_bump_version_pre` stderr WARN gap
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: Count/status behavior matches `check-bump-version.sh`; Python does not emit the `lib-count-commits.sh` stderr WARN on `missing_main_ref` (observability only).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.

---

**Merge notes (for voters, not part of machine schema):**
- **8+11+27**, **9+22**, **7+32**, **13+28** merged on identical behavioral risk.
- **FINDING_10** (correctness) kept separate from **FINDING_29** (dyn-bash OOS attestation): opposing scope on non-ASCII / custom bump paths.
- Input **FINDING_3** (structure: duplicate drop blocks) kept separate from **FINDING_8** (missing committed `bump_worktree` module) and **FINDING_26** (missing drop success parity test).
- Dyn-bash detailed “Suggested fix” prose lives in source concerns; all slots’ formal **Suggested revision** lines were the generic “Address the concern above.” and are quoted verbatim above.
