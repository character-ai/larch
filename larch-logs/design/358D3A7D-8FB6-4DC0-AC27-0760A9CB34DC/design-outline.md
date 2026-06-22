## Proposed Design Outline

### Goals
- Finish the `materialize-manifest-oos` sh-to-py migration that #3685 left incomplete: retire the now-orphaned Bash script and its harness.
- Remove the last subprocess hop in `implement_dispatch.py:_materialize_oos` by calling `file_oos.materialize_manifest_oos()` in-process.
- Reach `make lint-retired-scripts` clean with pytest covering the 6 shell-harness cases.

### Non-goals
- Re-porting manifest parsing, dedup-by-title, security routing, or the redaction sanitizer. Already done in `python/file_oos.py`.
- Changing redaction families or any redaction behavior. No `SECURITY.md` edit.
- Removing the `oos materialize-manifest` CLI verb. Keep it as the thin manual/test entrypoint.

### Approach sketch
- In-process: replace the `_invoke_cli(["oos","materialize-manifest",...])` count-only + full passes in `_materialize_oos` with direct `file_oos.materialize_manifest_oos()` calls; preserve the `materialize-manifest-oos.log` capture, `_append_materialize_oos_failure`, and `_oos_materialize_should_bail` bail logic.
- Retire: delete `materialize-manifest-oos.sh`/`.md` and `test-materialize-manifest-oos.sh`/`.md`; add both `.sh` paths to `python/migrated-scripts.tsv`.
- De-reference: drop the `residual-bash-paths.txt` test entry; fix the `--tool` label in `implement_dispatch.py` and the warning label in `file_oos.py`; update `skills/implement/SKILL.md` references so no tracked file cites the retired basenames.
- Test: port the 6 shell cases into `python/test_file_oos.py`.

### Surfaces in scope
- `python/implement_dispatch.py`, `python/file_oos.py`, `python/test_file_oos.py`
- `python/migrated-scripts.tsv`, `scripts/residual-bash-paths.txt`
- `skills/implement/SKILL.md`
- `skills/implement/scripts/materialize-manifest-oos.{sh,md}`, `skills/implement/scripts/test-materialize-manifest-oos.{sh,md}`

### Open questions
- None.
