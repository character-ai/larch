## Acceptance

- One definition per shared helper lives in `python/larch_io.py`. All duplicate `parse_kv` / `read_kv` / `read_kvs` / `kv_value` / `format_kvs` / `write_kvs` / `atomic_write` / `read_text` / `write_text` / `append_text` copies are deleted after their call sites repoint, except the documented parity exceptions kept local (see Edge cases): `session_env._read_kv_file_text`, `report_tokens_cost._parse_kv`, `design_lifecycle._read_env_value_last` / `_read_env_values`, shell-env readers, `dirty_tree._write_atomic`, and the deferred `agents.py` text-IO clones.
- Behavior is unchanged at every repointed call site: duplicate-key first/last-wins, missing-file defaults, per-site `cr_strip` mode, `skip_empty_key`, `on_error_default`, `empty_value_means_default`, symlink refusal, `O_EXCL` temp-create with stale-temp pre-unlink, `shutil.move` vs `os.replace`, and `errors=` decoding all match the prior local helper.
- On-disk wire formats are unchanged: the `KEY=value` stdout grammar and `.sh` env-file byte format are preserved. Refactor the parsing and writing, not the format. `write_kvs` raises `OSError`; bool-return success/failure stays in local wrappers only.
- `normalize_reviewer_label` is NOT moved; it stays in `python/review_pipeline.py`.
- `python/test_larch_io.py` covers the shared contract; `test_bootstrap`, `test_admission`, `test_session_env`, `test_file_oos`, and `test_plan_review` are updated for moved monkeypatch targets and per-site parity.
- `make py-lint`, `make py-test`, and `make lint` are green; no unused imports remain after local-copy deletion.
