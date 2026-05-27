# check-contains-pins.sh

Purpose: verify canonical `contains "$VAR" 'literal' 'label'` and `contains "$VAR" "literal" "label"` test-pin assertions by checking that the pinned literal exists verbatim in the file referenced by `$VAR`.

Primary callers: `scripts/relevant-checks.sh` invokes this script after changed-file pre-commit and direct relevant Make targets pass. Humans may also run `bash scripts/check-contains-pins.sh` for a full-repo scan or `bash scripts/check-contains-pins.sh --changed-files <file>` for a scoped scan.

Canonical v1 grammar: a single-line assertion whose first argument is a double-quoted shell variable and whose second argument is either a single-quoted literal or a static double-quoted literal. Static double-quoted literals containing `$` or backticks are skipped because shell expansion would make the verbatim target ambiguous.

Variable resolution: the scanner walks each `scripts/test-*.sh` and `skills/*/scripts/test-*.sh` file in order, recording prior assignments shaped as `VAR="$REPO_ROOT/<relative-path>"` or `VAR="$SCRIPT_DIR/../<relative-path>"`. Assertions whose variables cannot be resolved, or whose targets are absent, produce `UNRESOLVED_VAR` warnings without failing the run. In `--changed-files` mode, an assertion is in scope when either the referenced target file changed or the test script containing the assertion changed.

Exit codes: 0 means no defects, including the no-applicable-assertions case; 1 means at least one canonical literal was not found in its resolved target; 2 means argv or input-file error. Defects print as `DEFECT: <test-script>:<lineno>: literal '<literal>' not found in <target>`. Non-canonical assertion shapes print `SKIPPED_NON_CANONICAL` warnings and do not fail the run.

Non-goals: arrays of literals, heredoc literals, multi-line assertions, regex-shaped assertions, mixed-quote concatenations, escaped double-quote interpretation, and `bash -c`-wrapped invocations are outside v1 scope.

Makefile wiring: `make test-check-contains-pins` runs `scripts/test-check-contains-pins.sh`. The harness is also included in the `test-harnesses-15` shard.

Edit in sync: update `scripts/test-check-contains-pins.sh`, `scripts/relevant-checks.sh`, and `scripts/relevant-checks.md` when the CLI, warning text, exit codes, assertion grammar, or changed-file scoping behavior changes.
