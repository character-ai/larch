## Decision 1: Scope, given #3685 already ported the script
- **Question**: Issue #4969 asks to port `materialize-manifest-oos.sh` to Python and call it in-process, but #3685 already did the functional port. What scope should this run target?
- **Resolution**: "Cleanup + in-process". Finish the migration. Delete the orphaned `.sh`/`.md` and test `.sh`/`.md`. Port the 6 shell test cases to pytest. Record retired paths in `python/migrated-scripts.tsv`. Drop the `residual-bash-paths.txt` entry. Fix stale references (`skills/implement/SKILL.md`, `--tool` label strings). Convert `implement_dispatch.py`'s remaining Python-subprocess call (`_invoke_cli(["oos","materialize-manifest",...])`) to a direct in-process `file_oos.materialize_manifest_oos()` import.
- **Source**: user

## Decision 2: Already-completed work — do NOT re-port
- **Question**: What parts of the issue's scope are already satisfied in main?
- **Resolution**: `python/file_oos.py:materialize_manifest_oos()` is the full Python port: manifest parsing, title/description normalization, dedup-by-title, security routing to `security-oos-observations.md`, public-text sanitizer. `_sanitize_public_text()` reuses `redact secrets` in-process (calls `redact()`), then applies `_INTERNAL_URL_RE` / `_EMAIL_RE` / `_SSN_RE` / `_PHONE_RE` / `_ACCOUNT_RE`. Wired as `oos materialize-manifest` (`cli.py:380` -> `file_oos.materialize_manifest_main`). `--count-only` preserved. The dispatcher already calls the Python verb, not the `.sh`. Do not re-implement any of this.
- **Source**: codebase

## Decision 3: Hard constraints to preserve
- **Question**: What must not break?
- **Resolution**: Redaction parity (every PII family still redacted). Security-routing parity (security-signalled OOS go to `security-oos-observations.md`, not public filing). `--count-only` behavior. Dedup-by-title idempotency. Monotonic `OOS_N` allocation. The materialize-failure logging path in `implement_dispatch.py` (`_append_materialize_oos_failure` + `materialize-manifest-oos.log` capture + `_oos_materialize_should_bail`). `make lint-retired-scripts` must stay clean after retiring the path, which requires removing every tracked reference to the retired `.sh` basenames.
- **Source**: codebase + user

## Decision 4: SECURITY.md
- **Question**: Does this change redaction behavior enough to require a SECURITY.md update?
- **Resolution**: No. Redaction families are unchanged (parity preserved). No SECURITY.md edit required. Revisit only if a test reveals a parity gap in the existing Python sanitizer.
- **Source**: codebase + user
