### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/launch-codex-implement.sh:110-125
- **Concern**: Narrow grant has no symlink or full-tmpdir guard. Scenario: `codex-step2-out` can pre-exist as a symlink to `$IMPLEMENT_TMPDIR`; `SESSION_TMPDIR=$(cd "$MANIFEST_DIR" && pwd -P)` then equals the full session tmpdir and `--add-dir` widens again (review launchers reject symlinks via `[[ ! -L "$p" ]]`)
- **Proposed resolution**: After the manifest/qa parent check, reject symlink `MANIFEST_DIR`/`QA_PENDING_DIR` (mirror `launch-review.sh` `_codex_canonical_existing_dir`), then if `IMPLEMENT_TMPDIR` is set exit 2 when canonical `SESSION_TMPDIR` equals canonical `IMPLEMENT_TMPDIR`

