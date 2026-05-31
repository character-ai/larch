### FINDING_19: [OUT_OF_SCOPE] `git.py` inherits broad `os.environ`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Git helpers still inherit most of `os.environ`. Malicious env could point git at alternate object stores (pre-existing subprocess model). Extend `_git_subprocess_env` allowlist/denylist if hardening the git trust boundary repo-wide.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_20: [OUT_OF_SCOPE] Parity tests use `bash -c` with constructed scripts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Parity tests invoke `bash -c` with constructed scripts. No production exposure; scripts use fixed repo paths. No change required unless tests ever embed untrusted input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_29: [OUT_OF_SCOPE] `sorted_changed_files` / `LC_ALL=C` attestation (parity OK)
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: `files.sort(key=lambda s: s.encode("utf-8"))` in `python/bump_worktree.py:38-39` matches byte-order `sort` for UTF-8 paths; `test_sorted_changed_files_c_locale_order` covers non-ASCII ordering. Default drop guard string equality aligns with `drop-bump-commit.sh` / `drop-changelog-commit.sh`. (Contrasts with in-scope FINDING_10 on custom `LARCH_BUMP_FILES` / documented ASCII-only gap.)
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_30: [OUT_OF_SCOPE] `_today_iso()` matches shell `date`
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: `datetime.now().astimezone().date().isoformat()` matches `date +%Y-%m-%d` under the same `TZ` as the shell (format `YYYY-MM-DD`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_31: [OUT_OF_SCOPE] Idempotency helpers match bash
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: `_idempotency_transparent` / `_idempotency_ref` in `version_bump.py` match `idempotency_commit_is_transparent` (subject prefixes, `CHANGELOG.md`-only vs `larch-logs/**`, empty diff-tree, depth cap 3).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_32: [OUT_OF_SCOPE] KV booleans / Phase 7 `emit_kv` adapter
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: This phase returns frozen dataclass `bool`s, not stdout `APPLIED=true` / `COMMITTED=true` / `DROPPED=true`; parity tests normalize with `str(...).lower()`. Phase 7 needs an explicit `emit_kv` adapter (`true`/`false`, not `True`/`False`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_33: [OUT_OF_SCOPE] `apply_bump` unmerged exit mapping
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: `apply_bump` returns `ApplyResult(applied=False, …)` rather than exit 4; matches the plan (exit mapping is driver-side). ERROR text is shorter than `apply-bump.sh` (no `git merge/rebase --continue` hints); parity tests only compare `APPLIED`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


