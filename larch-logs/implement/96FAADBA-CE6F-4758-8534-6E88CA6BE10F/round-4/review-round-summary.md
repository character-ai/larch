# Review Round 4

- Mode: `diff`
- 3 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_5: Makefile pytest shard filter misses `test_main_accepts_global_flags_before_subcommand`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: New `test_main_accepts_global_flags_before_subcommand` is outside all three `test-stall-recovery-report-{1,2,3}` `pytest -k` shard filters; `lint-harness-pytest-partition.py` fails (91 tests, 90 covered); `make lint` fails via `test-harness-shards-coverage`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add main_accepts or global_flags to a shard -k expression (shard 1 recommended) and verify python3 scripts/lint-harness-pytest-partition.py passes


### FINDING_8: `populate_sensitive_corpus()` validates sensitive path after reading outside files
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: At `python/stall_recovery.py:1677-1697`, `populate_sensitive_corpus()` validates `--sensitive-corpus-file` only after `build_sensitive_corpus_from_evidence()` has already read it and written `${tmpdir}/...-sensitive-corpus.effective`. If a caller passes an absolute readable file outside `$IMPLEMENT_TMPDIR`, the helper returns failure, but it can leave that outside file’s contents copied into the tmpdir effective corpus artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Validate `sensitive_file` and other caller-supplied evidence paths before reading them, and delete any temporary effective corpus on every failure path.


### FINDING_9: `dedup-tier-a-report` ignores `design-failure` artifact prefix; reads wrong slice files
- **Reviewer(s)**: dyn-cutover-output.txt
- **Severity**: blocking
- **Concern**: At `python/stall_recovery.py:1069-1094` and `skills/design/scripts/design-failure-report.sh:150`, `dedup-tier-a-report` still hardcodes default slice paths as `stall-recovery-tier-a-{attempts,escalation,root-cause}.md`, while `compose-report` with `--artifact-prefix design-failure` writes prefixed `design-failure-tier-a-*` slices. `design-failure-report.sh` calls dedup with `helper_common` (`--profile generic --artifact-prefix design-failure`) but only passes `--body-file`; the dedup subparser does not accept `--artifact-prefix`, so those flags are dropped and dedup reads/writes the wrong files. On Tier A dedup hits (`dedup-comment`), `file-failure-report-cross-repo.sh` assembles comments from empty slices instead of the evidence `compose-report` just materialized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cutover-output.txt: Teach `dedup-tier-a-report` the same `--artifact-prefix` / `_artifact_path()` defaults as `compose-report`, wire the flags on its argparse surface (or honor leading global flags), and add a pytest case that composes with `design-failure` prefix then dedups and asserts the prefixed slice files are consumed.


