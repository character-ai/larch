### FINDING_1: Port design-log breadcrumb publish helpers before deleting lib-larch-log.sh
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan deletes `scripts/lib-larch-log.sh` before porting breadcrumb publish helpers and slug validation still used by `scripts/design-log-publish.sh`. `/design` log publish can fail and lose breadcrumb quiet-log forensics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add publish_breadcrumbs helpers to python/run_logs.py (or a run-log publish-breadcrumbs CLI verb) and rewrite scripts/design-log-publish.sh to call them instead of sourcing lib-larch-log.sh
  - From Cursor-Innovation: Add an explicit port step for breadcrumb publish helpers (or inline a minimal surviving bash surface in design-log-publish.sh) before lib-larch-log.sh deletion; do not assume CLI verbs alone satisfy design-log-publish


### FINDING_2: Preserve run-log commit from subdirectory parity
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan requires refusing commits from a repo subdirectory, but the bash implementation resolves the repo root from any in-repo current working directory. This breaks bash parity for internal callers launched below the repo root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Resolve consumer repo root from caller cwd (same as lib-larch-log.sh LARCH_LOG_REPO_ROOT) and run git -C that root; do not refuse solely because cwd is not the top-level directory


### FINDING_3: Include shared archetype pool in run-log commit
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: The commit port omits copying and committing `larch-logs/shared`. Dynamic archetype `archetype_ref` payloads can point at files that never land in the committed tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Port the _commit_shared_src/_commit_shared_repo copy and include larch-logs/shared in add/status/commit pathspecs inside larch_log_commit_main / _commit_run
  - From Codex-Pragmatic: Add explicit _commit_run steps to copy <LARCH_LOG_ROOT>/shared into <repo>/larch-logs/shared and include larch-logs/shared in scoped git pathspecs.


### FINDING_4: Specify full capture-session-transcript parity
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: The transcript port is described too narrowly as render, write, and commit. It omits status tokens, refresh retain behavior, no-commit and defer-commit paths, source recovery, and warning logging used by refresh and implement flows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Spell out full argv and stdout parity for capture_transcript_main in the plan and cover refresh retain, defer-commit, and status tokens in python/test_run_logs.py
  - From Codex-Pragmatic: Specify full capture-session-transcript flag/status parity, especially --no-logs-commit, --refresh-mode, --defer-commit, warning logging, and deferred commit behavior.


### FINDING_5: Make caller cutover exhaustive before deleting retired helpers
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-dyn-caller-sweep, Codex-dyn-caller-sweep
- **Severity**: important
- **Concern**: The cutover list omits live shell, skill, Python, and sourced-library references to retired helpers. Deleting the helpers can break `/design`, `/implement`, `/issue`, `/research`, check capture, rendering warnings, and redacted diagnostics even if the existing retired-script lint misses the references.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Expand the cutover inventory to an explicit grep-driven manifest (or require a pre-delete ripgrep gate listing every live reference) rather than treating lines 100-122 as exhaustive; keep make lint-retired-scripts as the final gate
  - From Codex-Innovation: Add these sourced libraries to the required cutover list and extend the retired-script sweep to catch basename references through non-SCRIPT_DIR variables, or run an explicit grep for retired helper basenames before deletion
  - From Cursor-Pragmatic: Expand the cutover inventory to every runtime caller of the retired scripts (grep for larch-log.sh, append-tool-failure.sh, append-execution-issue.sh, redact-secrets.sh, redact-tmpdir-paths.sh, refresh-run-logs.sh, scrub-log-secrets.sh, verify-skill-called.sh, capture-session-transcript.sh) and require each file in the plan Files section before deletion.
  - From Cursor-dyn-caller-sweep: Add python/rendering.py to the Python caller-cutover list; replace the bash subprocess with run-log append-entry (or a shared run_logs helper) preserving --log/--category/--entry semantics
  - From Codex-dyn-caller-sweep: Add these skills runtime callers to the cutover list, or replace the hand list with an explicit exhaustive scripts/ and skills/ stale-reference target that updates every hit to the new python/cli.py verbs


### FINDING_6: Preserve grep -E semantics for verify skill stdout-line
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan replaces `LC_ALL=C grep -E -q` with Python `re.search` for `--stdout-line`. POSIX ERE and Python regex semantics can diverge, including malformed-regex handling and pass/fail behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Port stdout-line matching with grep -E parity (subprocess with LC_ALL=C) or document and test an explicit ERE subset; do not use bare re.search as the parity mechanism
  - From Codex-Innovation: Preserve grep -E -q -- with LC_ALL=C from Python, or implement an equivalent POSIX ERE path with the same empty-regex and regex-error fail-closed behavior
  - From Cursor-Requirements: Specify stdout-line parity as grep -E (subprocess or equivalent): locale pinned, leading-dash safe, malformed-regex fail-closed; port `scripts/test-verify-skill-called.sh` Section 2 cases including exit-2


### FINDING_7: Use the correct schema v2 manifest immutable fields
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The plan names the wrong immutable manifest fields. A port following it can allow mutation of schema v2 provenance fields or reject fields that bash allows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Align larch_log_manifest_main immutable keys and error tokens with scripts/larch-log.sh manifest branch (lines 863-864); add pytest fixtures for each rejected key
  - From Codex-Innovation: Use the current immutable set for schema v2: schema_version, skill, run_id, started_at, operator_cwd, operator_repo_root. Do not substitute created_at/version unless the manifest schema is explicitly changed
  - From Codex-Requirements: Change the plan to reject schema_version, skill, run_id, started_at, operator_cwd, and operator_repo_root. Do not require created_at or version unless the schema actually adds them.


### FINDING_9: Retarget canonical run-log contract documentation
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-ref-sweep
- **Severity**: important
- **Concern**: The plan deletes `scripts/larch-log.md` and `scripts/larch-log-batches.md` but can leave AGENTS and run-log docs pointing at those removed contract sources.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Explicitly retarget AGENTS.md canonical entries to `docs/run-log-cli.md` and `docs/run-log-batches.md` (or fold into `docs/run-logs.md`) in the same PR that deletes the script siblings
  - From Cursor-dyn-ref-sweep: Plan creates docs/run-log-cli.md and docs/run-log-batches.md and says update AGENTS.md/run-logs.md to reference Python CLI but does not require repointing the canonical Authoritative sources entries from scripts/larch-log.md / scripts/larch-log-batches.md to the new docs paths lint-retired-scripts only forbids retired path strings; an implementer can satisfy lint with CLI one-liners while AGENTS.md Canonical sources and docs/run-logs.md Authoritative sources no longer index the moved contract docs the issue names as authorities In the docs section specify: AGENTS.md:43 and docs/run-logs.md:525-526 must list docs/run-log-cli.md and docs/run-log-batches.md as the run-log contract sources (not only python/cli.py mentions)


### FINDING_10: Preserve append-tool-failure optional metadata flags
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The append-failure port omits live optional flags such as status label, verdict, retry count, and transient retry count. Existing callers can be rejected or lose failure metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Require append_failure_main to accept and validate the four optional flags, preserve the header suffix format, and add focused pytest coverage for one metadata suffix plus invalid retry values.


### FINDING_11: Preserve scrub-log-secrets stdout keys
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The scrub-log-secrets contract omits `LARCH_SECRET_SCRUB_FILES`. This regresses the stdout contract and harness expectations even if current commit callers only consume the violation count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Require redact scrub-log-secrets to emit both keys and preserve fail-closed exit 2 and 3 behavior. Add pytest coverage for both stdout keys.


### FINDING_12: Update stale bare helper references in skill prose
- **Reviewer(s)**: Cursor-dyn-ref-sweep
- **Severity**: important
- **Concern**: The stale-reference lint may miss bare helper basenames in `SKILL.md` prose. Operators can follow stale instructions for deleted scripts even after the migration passes lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-ref-sweep: After script deletion lint can pass while skills/implement/SKILL.md still documents bare larch-log.sh / redact-secrets.sh / append-tool-failure.sh (e.g. :10,:26,:40,:737,:870 and skills/design/SKILL.md :453,:313); operators follow stale skill prose Add explicit UPDATED steps for skills/implement/SKILL.md and skills/design/SKILL.md (and other reference .md with bare names) to repoint to python3 python/cli.py run-log|redact|append-failure verbs; do not rely on lint alone for SKILL.md prose


### FINDING_13: Prune retired script entries from agent-lint allowlists
- **Reviewer(s)**: Cursor-dyn-ref-sweep
- **Severity**: important
- **Concern**: The plan omits `agent-lint.toml` cleanup for deleted scripts and harnesses still listed in dead-script allowlists. This can break lint or leave false exemptions after deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-ref-sweep: Stale allowlist rows for deleted paths (larch-log-flush.sh, verify-run-log-completeness.sh, larch-log-batches.sh, test-larch-log*.sh, test-append-tool-failure.sh, etc.) may break make lint/agent-lint or leave false exemptions Add ### UPDATED: agent-lint.toml — remove allowlist entries and comment blocks for every retired script and deleted harness in this migration


### FINDING_14:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:184-186
- **Concern**: [SCOPE-REDUCTION] The plan adds a new repo-root cwd requirement for run-log commit even though the current contract accepts any cwd inside the consumer worktree. Scenario: Existing callers that invoke the CLI from a subdirectory would start failing, despite scripts/larch-log.md documenting git rev-parse based worktree-root resolution
- **Proposed resolution**: Remove the subdirectory refusal edge case and preserve current git -C cwd rev-parse --show-toplevel behavior


### FINDING_15:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/larch-log.sh:6-9
- **Concern**: [SCOPE-REDUCTION] Plan adds a subdirectory commit refusal that contradicts caller-cwd consumer repo semantics. Scenario: A run-log commit launched from a consumer repo subdirectory fails even though the current bash contract resolves the worktree root from PWD and commits there
- **Proposed resolution**: Drop the non-repo-root cwd refusal. Resolve git root with git -C cwd rev-parse --show-toplevel, write under that root, and refuse only when cwd is outside a git worktree


### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:186; scripts/larch-log.md:151-167
- **Concern**: [SCOPE-REDUCTION] Commit subdirectory refusal is a parity regression. Scenario: The current contract resolves the consumer repo root from caller PWD, so invoking commit from a worktree subdirectory still commits to the repo root. The proposed refusal breaks that supported path and conflicts with the consumer-repo commit invariant.
- **Proposed resolution**: Remove the subdirectory-refusal edge case. Keep git -C cwd rev-parse --show-toplevel and place larch-logs under that resolved root.


### FINDING_17:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:184-186
- **Concern**: [SCOPE-REDUCTION] Plan adds a non-parity subdirectory commit refusal. Scenario: The current bash contract resolves the consumer repo from caller cwd, including subdirectories, via scripts/larch-log.sh:7-9 and scripts/lib-larch-log.sh:7-10. Refusing subdirectory cwd can break existing callers and conflicts with plan line 11.
- **Proposed resolution**: Remove the subdirectory refusal. Resolve the git top-level from cwd, fail only outside a git worktree, and keep the consumer-repo commit test.


### FINDING_18:
- **Reviewer(s)**: Codex-dyn-ref-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:124; python/migration_lint.py:210-217
- **Concern**: [SCOPE-REDUCTION] Plan allows migration-note and test retired-path references that the current lint target does not allow. Scenario: An implementer can leave a retired helper mention in migration notes because the plan permits it, but make lint-retired-scripts scans every tracked non-binary file except larch-logs, CHANGELOG.md, and the manifest, so verification fails after the cutover
- **Proposed resolution**: Remove the migration-notes and literal-test exceptions from the plan, or state that tests must construct retired names dynamically and only python/migrated-scripts.tsv may contain literal retired paths




### FINDING_1: Consumer run-log commits still target plugin root
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned Python commit path leaves internal run-log APIs hardcoded to the plugin repository and rejecting consumer subdirectory cwd values, so flush/finalize paths can fail or commit logs to the wrong tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Explicitly replace `_larch_log_commit` and `_publish_run_tree_to_repo` with shared `_commit_run` / `_resolve_consumer_repo_root(cwd)`; rewire `flush_logs_pre` and `commit_larch_logs` to that path; drop the subdir-rejection guard and update conflicting tests. Narrow or remove the line 171 `init_run()` carve-out so ship internals do not keep plugin-root commit behavior.
  - From Cursor-Pragmatic: Require the plan to replace `_larch_log_commit` and `_publish_run_tree_to_repo` with the new consumer-root resolver (same semantics as bash `larch-log.sh` lines 7-9), and drop the cwd-must-equal-plugin-root guard. Add/keep pytest coverage for plugin-cache vs consumer worktree on these internal APIs, not only CLI subprocess tests.


### FINDING_2: `redact secrets` needs secret-only semantics
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The plan does not specify that the replacement for `redact-secrets.sh` must scrub only secrets, which risks accidentally applying tmpdir or operator-path redaction to callers that expect secret-only behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add or name a secret-only helper for main_secrets, keep tmpdir rewriting only in redact tmpdir-paths or combined internal helpers


### FINDING_3: `lib-quiet.sh` still depends on deleted redact helper
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The cutover omits the surviving `lib-quiet.sh` streaming caller of `redact-secrets.sh`, so deleting the script can break diagnostic redaction in shell scripts that source the quiet library.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add scripts/lib-quiet.sh to surviving-shell cutovers: invoke python3 "$PLUGIN_ROOT/python/cli.py" redact secrets --streaming --state-file … (or shared redact helper); extend test_redact.py PEM streaming coverage to exercise the lib-quiet call path


### FINDING_4: Stale-reference sweep misses config and policy files
- **Reviewer(s)**: Codex-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The stale-reference sweep omits tracked configuration and policy files that name retired helpers, so lint or secret-scan allowlists can retain deleted script paths after the migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add .gitleaks.toml and .pre-commit-config.yaml to the stale-reference sweep/update list; remove deleted script allowlist entries from .gitleaks.toml and update the pre-commit comment to the new Python redaction surface
  - From Cursor-Requirements: Extend stale-reference sweep to .gitleaks.toml and SECURITY.md; repoint allowlist to python/redact.py and python/test_*.py


### FINDING_5: `flush_logs_post()` must remain post-merge tmpdir-only
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan groups `flush_logs_post()` with refresh cutover even though it must preserve post-merge manifest and final-report behavior without committing or routing through pre-flush refresh semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Revise the plan to preserve `flush_logs_pre` and `flush_logs_post` as separate public APIs: only pre-flush may commit; post-flush must remain tmpdir-only and must not call `run-log refresh` or `_commit_run`


### FINDING_9: Run-log failure envelope is underspecified
- **Reviewer(s)**: Codex-dyn-bash-contract-fidelity
- **Severity**: important
- **Concern**: The plan specifies the success envelope but not the existing failure envelope, including `ERROR=`, fixed zero or empty fields, exit tiers, and stderr-only refusal paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-bash-contract-fidelity: Add the failure contract to the run-log verb spec: preserve LOG_WRITTEN=false, empty LOG_PATH/SHA256/COMMIT_SHA, BYTES=0, UNCHANGED=false, ERROR=<message>, current exit codes 1/2/3, plus the existing stderr-only post-merge/default-branch commit refusals.


### FINDING_10: Transcript capture must log every terminal status
- **Reviewer(s)**: Codex-dyn-bash-contract-fidelity
- **Severity**: important
- **Concern**: The transcript capture plan preserves warning logging only for failure-like statuses, but the current contract records execution-issue warnings for every terminal status, including successful or retained states.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-bash-contract-fidelity: Revise capture_transcript_main to append a Warnings entry for every terminal status, including captured, suppressed-no-logs-commit, commit-failed, and missing-source retain paths; keep source-recovery basename-only logging.


### FINDING_11:
- **Reviewer(s)**: Codex-dyn-cutover-completeness
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:263,282,510; python/migrated-scripts.tsv:108-111
- **Concern**: [SCOPE-REDUCTION] Plan re-adds already migrated nonexistent script targets scripts/sanitize-mermaid-fragment.sh and scripts/upsert-diagrams-comment.sh. Scenario: Those files are already recorded as migrated under #3675 and are absent from the repo, so B3 would send implementation work to dead targets outside this issue's run-log migration surface.
- **Proposed resolution**: Remove those two script names from B3 cutover and md-sibling lists. Keep any needed reference updates on the existing Python surfaces.




### FINDING_1: Preserve volatile-only run-log commit skip
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The `_commit_run` port may drop the Python-only volatile refresh detection, cleanup, internal signal, and `REFRESH_SKIP_VOLATILE_ONLY` mapping, causing pre-push flushes to create or mishandle commits for refresh-only files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `_commit_run` (and tests), explicitly preserve volatile-only detection/cleanup and the `larch-log-volatile-only` internal signal; keep `flush_logs_pre` mapping to `config.REFRESH_SKIP_VOLATILE_ONLY`. Port `_VOLATILE_REFRESH_BASENAMES` helpers with the existing `test_run_logs.py` volatile-only cases.


### FINDING_3: Keep breadcrumb staging separate from commit flow
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Deleting `lib-larch-log` without a non-committing breadcrumb replacement may force design publish to use run-log commit semantics and change pause or final publish behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Expose the ported breadcrumb staging as a narrow helper/CLI and update design-log-publish to call it before deleting lib-larch-log; do not substitute run-log commit for the custom design publish commit flow.


### FINDING_4: Avoid legacy manifest v1 writes during schema v2 migration
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Internal manifest updates may still use the legacy `Manifest` dataclass after CLI init writes schema v2, producing hybrid manifests and confusing completeness or final-report readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Route all internal manifest mutations through the same schema v2 read/write helpers as `larch_log_manifest_main`; drop the plan carve-out to preserve legacy `init_run()`/`Manifest` v1 writes on recovery paths


### FINDING_6: Preserve path redaction for breadcrumbs
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The breadcrumb helper may narrow redaction to secrets only, allowing session tmpdirs or operator repo paths into committed breadcrumb logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Keep the breadcrumb pipeline combined: apply tmpdir/operator path redaction before streaming PEM secret redaction, or add an explicit combined helper for breadcrumb files


### FINDING_7: Preserve lib-quiet fd-3 routing in Python replacements
- **Reviewer(s)**: Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Python ports of scripts that sourced `lib-quiet.sh` may emit machine-readable KVs on stdout or inherited fd 3 incorrectly, breaking callers that parse captured stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: For new mains replacing scripts that sourced lib-quiet, call logging_util.quiet_init(argv0=<old basename>) before emit or emit_kv and add inherited-quiet coverage; keep pure stdin/stdout filters quiet-disabled
  - From Cursor-Requirements: Add quiet_init/emit_kv (logging_util contract stream) to append_entry_main and append_failure_main; mirror bash stderr routing for usage and I/O errors; extend pytest to assert no KV leak on stdout when quiet is active.


### FINDING_9: Redact append-mode run-log records before append
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Append-mode run-log batches may validate and append records without the existing tmpdir and secret redaction stage, allowing sensitive values into committed logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Revise larch_log_append_main to redact tmpdir paths and secrets into a staged record before sanitizer validation and append; add focused pytest coverage for append redaction


### FINDING_10: Delete redaction harness contract docs with harnesses
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The migration may delete redaction `.sh` harnesses but leave stale `.md` contract siblings and migration metadata references.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add scripts/test-redact-secrets.md and scripts/test-redact-tmpdir-paths.md to the deleted harness list and python/migrated-scripts.tsv


### FINDING_11: Keep `run-log exists` validation failures nonzero
- **Reviewer(s)**: Cursor-dyn-envelope-parity, Codex-dyn-envelope-parity
- **Severity**: important
- **Concern**: The plan overstates `run-log exists` as unconditional exit 0, which may mask invalid argv, missing log roots, invalid slugs, or unknown batches as successful probes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-envelope-parity: Qualify the contract: exit 0 only on valid argv when probing batch presence; keep `larch_log_fail` exit 1/2/3 for all other paths.
  - From Codex-dyn-envelope-parity: Narrow the plan and tests to say `exists` exits 0 only after argument, log-root, slug, and batch validation succeeds. Preserve current `larch_log_fail` exit 1 behavior for validation failures.


### FINDING_12: Preserve refresh commit-failed envelope
- **Reviewer(s)**: Cursor-dyn-envelope-parity
- **Severity**: important
- **Concern**: `refresh_run_logs_main` may omit the bash wrapper’s `REFRESH_COMMITTED=false REASON=commit-failed` stdout line and optional collapsed `ERROR=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-envelope-parity: Document and test the commit-failed line (including optional `ERROR=`) in `refresh_run_logs_main` and `docs/run-log-cli.md`.


### FINDING_13: Keep refresh skip reasons to bash parity
- **Reviewer(s)**: Cursor-dyn-envelope-parity
- **Severity**: important
- **Concern**: `refresh_run_logs_main` may leak ship-internal `flush_logs_pre` skip tokens instead of the bash refresh wrapper’s limited stdout reason enum.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-envelope-parity: Wire `refresh_run_logs_main` directly to `refresh-run-logs.sh` parity (bash REASON enum + single-line stdout), not `RefreshSkip` from `flush_logs_pre()`.


### FINDING_14: Preserve capture-transcript always-exit-0 contract
- **Reviewer(s)**: Cursor-dyn-envelope-parity
- **Severity**: important
- **Concern**: `capture-transcript` may return nonzero for usage or failure statuses, regressing the existing contract that all terminal statuses exit 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-envelope-parity: Pytest and `capture_transcript_main` should assert exit 0 for every terminal status, matching the bash wrapper.


### FINDING_15: Keep flush scrub count off stdout
- **Reviewer(s)**: Codex-dyn-envelope-parity
- **Severity**: important
- **Concern**: `run-log flush` may expose `SECRET_SCRUB_VIOLATIONS` on stdout even though the retiring wrapper only emits a stderr warning after parsing commit output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-envelope-parity: Keep `SECRET_SCRUB_VIOLATIONS=N` on `run-log commit` only. For `run-log flush`, parse the commit output and emit only the current stderr warning text when the count is greater than zero.


### FINDING_16: Preserve malformed-regex no-envelope verifier path
- **Reviewer(s)**: Codex-dyn-envelope-parity
- **Severity**: important
- **Concern**: `verify skill-called` may report malformed regular expressions as normal `VERIFIED=false` results instead of preserving the current internal-fault path with no key-value envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-envelope-parity: Specify that grep exit 2 exits 1, writes only the current stderr diagnostic, and emits no KEY=VALUE envelope. Add the pytest assertion for no `VERIFIED=` output.


### FINDING_18:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: plan.txt:468-471; python/migration_lint.py:1-5; docs/python-migration.md:68-73
- **Concern**: [SCOPE-REDUCTION] Bare-basename retired-script lint broadens a documented path-precise contract. Scenario: The migration can satisfy this stale-reference sweep with targeted grep, while changing lint-retired-scripts to repo-wide basename matching risks false positives against unrelated live files and contradicts the current linter contract.
- **Proposed resolution**: Keep lint-retired-scripts path-precise; run a migration-local bare-basename sweep or add a narrow temporary check for this retired-name set.


### FINDING_19:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: docs/python-migration.md:68-73
- **Concern**: [SCOPE-REDUCTION] Plan expands lint-retired-scripts to bare-basename coverage despite the path-precise linter contract. Scenario: The migration linter would take on broader false-positive-prone behavior that is not required for this B3 cutover; the feature only needs a one-time stale-reference sweep plus existing retired-path lint
- **Proposed resolution**: Keep lint-retired-scripts path-precise; run the planned grep sweep for bare basenames without changing the linter contract




### FINDING_1: flush_logs_pre can miss vendor diagnostics staging
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Python callers of `flush_logs_pre` can bypass vendor-failure-diagnostics staging that bash refresh and flush paths perform before commit, so CI-retry pushes may omit `vendor-failure-diagnostics.ndjson`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extract a shared pre-commit staging helper (vendor diagnostics, execution-issues flushes, transcript defer) and call it from flush_logs_pre, refresh_run_logs_main, and larch_log_flush_main; add a pytest that flush_logs_pre stages vendor diagnostics when slot parts exist.


### FINDING_2: shared archetype pool may commit unredacted reviewer content
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Shared reviewer archetype files can be hashed and committed before redaction, leaking tmpdir paths or secret-shaped tokens through `larch-logs/shared`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Redact reviewer-dyn-*.md to a temp file before hashing/copying into the pool, hash redacted bytes, write only redacted pool entries, and make _commit_run scrub every committed log root including larch-logs/shared with aggregated SECRET_SCRUB_VIOLATIONS


### FINDING_4: lib-quiet redaction cutover depends on undefined PLUGIN_ROOT
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: `lib-quiet.sh` may call the Python redaction CLI through undefined `PLUGIN_ROOT` under `set -u`, causing quiet error paths to abort or lose streaming redaction after the bash redactor is deleted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Resolve the CLI from lib-quiet itself, for example via LARCH_LIB_QUIET_DIR/../python/cli.py or a CLAUDE_PLUGIN_ROOT fallback, and keep the existing missing-redactor fallback and PEM state behavior.


### FINDING_5: batch registry omits plan-goals-test
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The Python batch registry may reject `--batch plan-goals-test`, causing Step 1 plan-goals artifacts to be skipped after caller cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add plan-goals-test .md replace plan-goals to the Python batch registry and port the plan-goals sanitizer, with matching docs and tests.


### FINDING_6: design log publish cutover omits init and scrub gates
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-sweep-gap-detection
- **Severity**: important
- **Concern**: `design-log-publish.sh` still uses retired run-log initialization and scrub helpers, so `/design` log publish can fail after bash deletion even if breadcrumbs are ported.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Expand the design-log-publish cutover to also switch init to run-log init and the pre-commit scrub gate to python3 python/cli.py redact scrub-log-secrets preserving LARCH_SECRET_SCRUB_VIOLATIONS parsing and fail-closed exits
  - From Cursor-dyn-sweep-gap-detection: Expand the `scripts/design-log-publish.sh` cutover bullet to require `run-log init` (same argv as today’s `larch-log.sh init` at lines 287-292) and update `scripts/design-log-publish.md` step 4 accordingly; keep custom worktree commit and do not route the full publish through `run-log commit`.


### FINDING_8: surviving harnesses may still copy deleted bash helpers
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Several surviving lint and integration harnesses still copy or link bash helpers planned for deletion, so `make lint` or `py-test` may fail after cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: After `scripts/redact-secrets.sh` and peers are removed, setup in `test-step-7a.sh`, `test-ci-wait.sh`, `test-collect-findings.sh`, `test-lint-fix-loop.sh`, `test-dispatch-plan-voters.sh`, design publish/render harnesses, `test-implement-bootstrap-invoke.sh`, `test-write-final-report.sh`, `test-step-18b-final-report.sh`, and `python/test_checks_bash_parity.py` hard-fail on copy; `make lint` / `py-test` cannot go green despite DoD Add an explicit UPDATED subsection for surviving integration harnesses and `python/test_checks_bash_parity.py`: repoint fixtures to `python3 …/cli.py redact secrets` (or minimal stubs), and list the affected `test-*.sh` files in the Makefile/harness update scope


### FINDING_9: volatile-only commit path lacks stdout envelope parity
- **Reviewer(s)**: Cursor-dyn-envelope-verb-spec, Codex-dyn-envelope-verb-spec
- **Severity**: important
- **Concern**: The Python `run-log commit` volatile-only path may preserve an internal signal without emitting the bash no-change stdout envelope, causing refresh callers to treat a no-op volatile skip as a commit failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-envelope-verb-spec: In `larch_log_commit_main`, map volatile-only to the same stdout contract as bash no-change commit: `LOG_WRITTEN=false`, `UNCHANGED=true`, empty `COMMIT_SHA`, remaining keys present; document this branch in `docs/run-log-cli.md`
  - From Codex-dyn-envelope-verb-spec: Add a commit CLI spec and pytest case for volatile-only stdout: LOG_WRITTEN=false, empty COMMIT_SHA, UNCHANGED=true, no git commit.


### FINDING_10: verify skill-called plan omits failure REASON enum parity
- **Reviewer(s)**: Codex-dyn-envelope-verb-spec
- **Severity**: important
- **Concern**: The Python `verify skill-called` port may collapse distinct bash failure reasons while still passing the planned tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-envelope-verb-spec: Spell out all existing REASON tokens in python/verify_skill.py plan and add pytest assertions for each exit-0 false path.




### FINDING_1: Surviving harness inventory uses wrong or incomplete skills paths
- **Reviewer(s)**: Cursor-Arch, Codex-dyn-cutover-inventory
- **Severity**: important
- **Concern**: The surviving harness list names nonexistent `scripts/...` paths and may miss required fixture updates for actual `skills/...` harnesses. This can leave retired-helper references in tests, including step-7a redaction fixtures, so deletion gates or migrated harnesses fail at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add skills/implement/scripts/test-step-7a.sh to the surviving integration harness list (or fix the path on line 498)
  - From Codex-dyn-cutover-inventory: Replace those plan entries with the actual skills/... paths and list the helper families each harness must repoint or stub via python/cli.py.


### FINDING_2: verify skill-called REASON enum breaks stdout contract
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-envelope-parity, Codex-dyn-envelope-parity
- **Severity**: important
- **Concern**: The planned Python port renames stable `verify-skill-called.sh` `REASON` tokens and may change commit-delta mismatch from exact equality to threshold semantics. Callers and tests that parse `missing_path`, `not_regular_file`, `empty_file`, `missing_stdout_file`, or `commit_delta_mismatch` can fail or lose parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Preserve the current REASON enum and exact commit-delta equality semantics in python/verify_skill.py and python/test_verify_skill.py: missing_path, not_regular_file, empty_file, missing_stdout_file, no_match, commit_delta_mismatch, missing_main_ref, git_error, ok
  - From Codex-Innovation: Keep the current REASON enum exactly, and update python/test_verify_skill.py expectations to assert missing_path, not_regular_file, empty_file, missing_stdout_file, no_match, commit_delta_mismatch, missing_main_ref, git_error, and ok
  - From Cursor-Pragmatic: Port the exact REASON vocabulary from `scripts/verify-skill-called.sh` (lines 40-55) and update `python/test_verify_skill.py` assertions to match; do not rename to shorthand tokens
  - From Codex-Pragmatic: Preserve the existing REASON enum and exact commit-delta mismatch behavior in python/verify_skill.py and update planned tests to assert missing_path empty_file not_regular_file missing_stdout_file no_match commit_delta_mismatch missing_main_ref git_error and ok
  - From Codex-Requirements: Update the plan and tests to preserve the current enum from `scripts/verify-skill-called.sh`: `ok`, `missing_path`, `not_regular_file`, `empty_file`, `missing_stdout_file`, `no_match`, `commit_delta_mismatch`, `missing_main_ref`, and `git_error`; keep exact delta comparison
  - From Cursor-dyn-envelope-parity: Replace plan REASON enum and test assertions with the full bash vocabulary from verify-skill-called.sh lines 40-54; map sentinel failures to missing_path not_regular_file empty_file; map commit-delta failure to commit_delta_mismatch
  - From Codex-dyn-envelope-parity: Implement the bash enum exactly: ok, missing_path, not_regular_file, empty_file, missing_stdout_file, no_match, commit_delta_mismatch, missing_main_ref, git_error; drop no_sentinel and count_too_low


### FINDING_5: lib-quiet redactor path can abort under set -u
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The planned `lib-quiet.sh` redactor path expands `CLAUDE_PLUGIN_ROOT` directly. Surviving callers may source `lib-quiet.sh` under `set -u` without defining that variable, so error paths can abort instead of using the current redactor-unavailable fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Resolve the CLI with a safe fallback such as ${CLAUDE_PLUGIN_ROOT:-$(cd "$LARCH_LIB_QUIET_DIR/.." && pwd -P)} and treat an unresolved or missing cli.py like the existing redactor-unavailable fallback; never expand a bare unset variable


### FINDING_6: refresh-run-logs plan misses token/timing JSON parity chain
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `refresh_run_logs_main` does not pin the existing bash token and timing refresh chain. An implementer can reuse an NDJSON-only path and fail to write `token-report.json` or `timing-report.json`, which completeness checks require.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In `refresh_run_logs_main`, spell out bash parity: subprocess `scripts/token-report.sh` and `scripts/timing-report.sh` with session-env exports, then in-process `_write_batch` for `token-report` and `timing-report` JSON inputs; do not substitute NDJSON-only `_render_token_timing_batches` on this path. Add pytest asserting those `.json` files exist after refresh.


### FINDING_7: append-failure cutover omits launcher callers
- **Reviewer(s)**: Cursor-dyn-cutover-inventory, Codex-dyn-cutover-inventory
- **Severity**: important
- **Concern**: The append-failure cutover list omits runtime launchers that still invoke `append-tool-failure.sh`. After deletion, launcher failure logging can become a guarded no-op or keep stale deleted-helper references.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-cutover-inventory: Add scripts/launch-review.sh to the explicit append-failure cutover inventory (and cut over append_launch_failure to run-log append-failure)
  - From Codex-dyn-cutover-inventory: Add both scripts to the append-failure cutover list and route the shown calls to python3 "$PLUGIN_ROOT/python/cli.py" run-log append-failure with existing metadata flags.



