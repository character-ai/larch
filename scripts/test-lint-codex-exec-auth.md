# test-lint-codex-exec-auth.sh

Black-box harness for `scripts/lint-codex-exec-auth.sh`.

Pinned cases:

- clean tree passes
- raw shell `codex exec` fails outside allowlisted launchers
- allowlisted `launch-codex-exec.sh` may contain the raw dispatch
- inline `# lint-codex-exec-auth: ok ...` pragma suppresses a fixture
- shell continuation `codex \` followed by `exec ...` fails
- `B=codex exec ...` and `A=1 B=codex exec ...` fail
- `CODEX_HOME=... codex exec ...` fails outside allowlisted launchers
- markdown bash-fence continuation `codex \` followed by `exec ...` fails
- invalid `--root` exits 2
