G-Fix-1: Aligned. Both abort path and Step 6 are fixed via a shared reap_pid_residuals helper.
G-Cfg-3: Aligned. _step0_parsed_env_path in session_env.py is the single canonical helper; _parsed_cache_path in design_step0_env.py delegates to it so write and reap share one source.
G-Py-4 (narrow deviation): reap_pid_residuals suppresses FileNotFoundError only. Justified: PID files may be absent when an abort occurs before session setup completes or when a prior cleanup already removed them. This is a documented narrow degraded path per G-Py-4 exception language. Unexpected OSError surfaces.
G-Sec-4: Aligned. Paths are constructed exclusively via _design_symlink_path / _design_run_path / _step0_parsed_env_path, all under Path.home()/.cache/larch/sessions/. cleanup_cache_sessions_root() is explicitly excluded.
G-Idem-1: Aligned. FileNotFoundError suppression makes reap_pid_residuals idempotent on re-run.
G-Wire-1: Aligned. --reason / --tool flags have defaults preserving the documented degraded-tools caller behavior.
All other guidelines: clean.
