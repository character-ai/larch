G-Py-4 deviation: reap_pid_residuals suppresses OSError silently. Justified: PID-file cleanup is best-effort; FileNotFoundError is normal when files are absent or were never created. This is a documented narrow degraded path per G-Py-4 exception language.
G-Sec-4: PID paths are bounded to ~/.cache/larch/sessions/ by construction via _design_symlink_path / _design_run_path / inline f-string; containment is enforced by the helpers. No freeform path input.
All other guidelines: clean.
