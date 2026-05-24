# test-launch-claude-ci.sh

Argv and prompt-shape harness for `scripts/launch-claude-ci.sh`.

Coverage:

- invalid / missing role rejection
- absolute `--output` path validation and unsafe-character rejection
- `--conflict-files` rejected for `--role fix`
- relative `--plan-file` rejection
- `--failure-log` containment under `$IMPLEMENT_TMPDIR` (absolute path, existing file)
- `<<<FAILURE_LOG_EXCERPT>>>` delimiter presence and `redact-secrets.sh` pipeline reference
- `claude-ci-fix` timing allow-list entry
- fix-role prompt includes literal `topology.tsv` when the shared CI-fix patterns file exists; `resolve-conflict` omits it

The harness sets `IMPLEMENT_TMPDIR` to an isolated tempdir so `--failure-log` validation cannot point at arbitrary host paths.

Wired as `make test-launch-claude-ci` (see `Makefile` / `test-harnesses-2`).
