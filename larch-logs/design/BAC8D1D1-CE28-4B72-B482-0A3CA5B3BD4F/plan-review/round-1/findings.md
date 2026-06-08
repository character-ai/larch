### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:22-29 / python/test_session_env.py
- **Concern**: Predicate 2 writer-target validator must name XDG-aware cache_sessions_root() explicitly and pytest must cover XDG session tmpdir writes. Scenario: Plan hardcodes ~/.cache only for the design-env symlink carve-out; if predicate 2 is implemented with the same hardcoded root, session-setup creates tmpdirs under $XDG_CACHE_HOME/larch/sessions and write-env / persist-run-flags / restore-finalize-state writes are rejected by NEVER #14 guard
- **Proposed resolution**: In predicate 2 spell out reuse of moved cache_sessions_root() (same logic as scripts/session-setup.sh session_cache_root); add test_session_env.py case with XDG_CACHE_HOME set asserting writer-guard accepts session file writes under XDG sessions root while symlink stays under ~/.cache/larch/sessions

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-skill-md-flag-signature.sh:74-91; scripts/test-lint-skill-md-flag-signature.sh:121-146; plan.txt:86
- **Concern**: [SCOPE-REDUCTION] Plan retargets shell-only flag-signature fixtures to python/cli.py without changing the linter resolver. Scenario: The resolver only inspects */scripts/*.sh tokens, so a fixture using python3 .../cli.py session write-run-params is ignored; existing assert_lint_fails_for cases then fail or lose verification, blocking make lint
- **Proposed resolution**: Do not point this shell-linter fixture at the Python CLI unless the linter gains a session-verb metadata source; minimum-change fix is to replace the retired write-run-params fixture with a non-retired shell fixture and cover write-run-params flags in test_session_env.py

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:24; scripts/test-check-reviewers.sh:512-520; skills/implement/scripts/test-implement-review-token-propagation.sh:37-42,70-75
- **Concern**: Strict writer-target validator conflicts with surviving session-setup --write-session-env callers. Scenario: Plan allows only claude-implement/design/review/research session dirs, but surviving make lint harnesses write session env files under arbitrary /tmp paths and one uses prefix larch-tchkrev-ss; after cutover these calls will be rejected or the guard will be weakened ad hoc
- **Proposed resolution**: Update the cutover plan for these surviving callers: use accepted claude-* prefixes and place --write-session-env outputs under an allowed claude-* temp/session directory, or make session setup write to its freshly created SESSION_TMPDIR/session-env.sh

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/session_env.py (restore-finalize-state verb)
- **Concern**: Plan lacks a parity test for raw-RHS reads of ship-pr-state values containing shell metacharacters or extra `=` bytes. Scenario: The moved `read_finalize_state` uses shlex parsing; if `restore-finalize-state` accidentally reuses it, `PR_TITLE`/`PR_URL` values with quotes, `$()`, or embedded `=` are corrupted and Step 18 `implement-finalize.sh teardown` reads wrong stall/PR metadata
- **Proposed resolution**: Add an explicit pytest (and retargeted harness case) with ship-pr-state fixtures like `PR_TITLE=Implement $(echo x)=y` asserting byte-identical round-trip via the dedicated raw reader only

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: code-quality
- **Location**: plan.txt:121
- **Concern**: [SCOPE-REDUCTION] Stale-reference sweep says ALL tracked files even though retired-script lint excludes larch-logs and CHANGELOG. Scenario: Implementer may churn historical larch-logs references that are intentionally excluded by python/migration_lint.py and docs/python-migration.md, creating unnecessary scope and merge risk
- **Proposed resolution**: Limit the sweep to lint-retired-scripts scanned files: exclude larch-logs, CHANGELOG.md, and the manifest itself

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/session_env.py:22-25
- **Concern**: Writer-target validator does not pin XDG-aware cache-sessions root. Scenario: Implementer uses hardcoded ~/.cache for predicate (2) while session-setup creates tmpdirs under XDG_CACHE_HOME; session write-env/persist-run-flags fail NEVER #14 guard on valid session dirs
- **Proposed resolution**: Document predicate (2) uses XDG-aware cache_sessions_root() matching session-setup.sh and cleanup-tmpdir.sh; reserve hardcoded ~/.cache only for the design-env symlink validator

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/session_env.py:20
- **Concern**: python/finalize.py:64-68. Scenario: Plan mirrors _write_finalize_text_safely instead of moving it with write_finalize_state_merged
- **Proposed resolution**: Duplicated atomic-write logic can diverge from ship finalize-state writes and weaken symlink/O_EXCL guarantees Move _write_finalize_text_safely into session_env.py with write_finalize_state_merged; import back from finalize.py

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-check-reviewers.sh:512-520; skills/implement/scripts/test-implement-review-token-propagation.sh:37-42,70-75
- **Concern**: Writer-target guard plan misses surviving --write-session-env harness outputs outside accepted session dirs. Scenario: The proposed strict writer validator only accepts real claude-* session targets, but these surviving make lint harnesses still ask session setup to write session-env files to arbitrary scratch paths or custom prefixes, so the cutover can make lint fail even if the runtime feature works
- **Proposed resolution**: Retarget these surviving harnesses during call-site cutover: use the session CLI and place written session-env files under validator-accepted claude-review/claude-implement temp dirs, or explicitly include equivalent harness rewrites in the plan

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/read-workflow-path.sh:52-57
- **Concern**: Plan deletes read-design-classification.sh but does not list read-workflow-path.sh for update; its third fallback shells out to that script and applies HARD-default semantics when python3/jq cannot resolve workflow_path/design_classification. Scenario: After cutover the -x probe fails, timing-report.sh loses the HARD fallback and emits unknown for the same run-params/timing artifacts bash classified as HARD today, changing report grouping
- **Proposed resolution**: Add scripts/read-workflow-path.sh under Files to modify: replace the dirname probe with python3 …/cli.py session read-classification (preserve HARD-default-on-invalid behavior, not only SIMPLE|HARD stdout)

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/session_env.py:22-25
- **Concern**: NEVER #14 writer-target predicate 2 requires a claude-*- basename on write-env targets, but session-setup today calls write-session-env with --write-session-env to caller-chosen paths under /tmp with no prefix check (skills/implement/scripts/test-implement-review-token-propagation.sh:37-42). Scenario: setup --write-session-env preserved in the plan would reject legitimate secondary session-env files outside claude-prefixed tmpdir names, breaking nested token-propagation parity and any caller using that flag
- **Proposed resolution**: Scope the prefix check to the session tmpdir created by setup (or to $IMPLEMENT_TMPDIR/session-env.sh / plugin-root.env writes); for setup --write-session-env allow broad /tmp|cache-root containment only, matching current bash which validates values but not output dirname prefix

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-implement-review-token-propagation.sh:16-18
- **Concern**: Call-site cutover lists implement-finalize.sh and bootstrap resume-tail but not this surviving harness; it still invokes session-setup.sh and read-session-env-key.sh directly. Scenario: Post-deletion make test-implement-review-token-propagation (if still wired) or nested-review CI paths fail at script-not-found despite token rehydration being production-critical
- **Proposed resolution**: Explicitly add this harness to the grep-driven cutover (session setup/read-key CLI paths) or fold its assertions into python/test_session_env.py and drop the bash harness in the same Makefile/agent-lint pass

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:22-24; scripts/test-check-reviewers.sh:512-520; skills/implement/scripts/test-implement-review-token-propagation.sh:25-42
- **Concern**: 1. Writer-target validator hard-codes only four claude prefixes while preserved setup --prefix/--write-session-env callers use custom prefixes and output paths. Scenario: After cutover, surviving make lint harnesses that exercise check-reviewers and nested review token propagation call session setup with --write-session-env outside an allowed claude session dir, so the new guard rejects the write and the required verification gate fails
- **Proposed resolution**: Amend the plan to either validate setup-owned writes against the freshly created session tmpdir/prefix contract or explicitly retarget these surviving harnesses to allowed claude session output paths before enabling the guard

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_session_env.py:1-1
- **Concern**: `test_session_env.py` omits `test-session-env-roundtrip.sh` H.* `--run-id`/`LARCH_RUN_ID` cases despite naming that harness as replaced. Scenario: `implement-bootstrap.sh` `_persist_larch_run_id()` rewrites `session-env.sh` via a second `write-env` call with `--run-id`; losing H.1–H.4 coverage after harness deletion leaves RUN_ID rehydration regressions unguarded by permanent pytest
- **Proposed resolution**: Add explicit pytest cases for valid `--run-id` → `LARCH_RUN_ID` round-trip, invalid run-id rejection, and absent `--run-id` omitting the key (port H.1–H.4 from `scripts/test-session-env-roundtrip.sh`)

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/write-design-current-env.sh:216-228
- **Concern**: write-design-env guard allowlist omits required source-env keys. Scenario: The plan says the writer-guard validates write-design-env output against an explicit allowlist, but the current design env contract always writes DESIGN_TMPDIR, SESSION_TMPDIR, and SESSION_ID and may write CLAUDE_PLUGIN_ROOT; the proposed allowlist omits those keys, so the port would either reject normal write-design-env calls or drop keys required by /design rehydration
- **Proposed resolution**: Add DESIGN_TMPDIR, SESSION_TMPDIR, SESSION_ID, and CLAUDE_PLUGIN_ROOT to the write-design-env allowlist, and cover a normal guarded source-env write containing those keys in test_session_env.py

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-emitter-routing-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/read-workflow-path.sh:52-54
- **Concern**: After hard cutover the `[[ -x …/read-design-classification.sh ]]` fallback never runs because that bash script is deleted; plan only names read-workflow-path.sh in the grep cutover list without specifying how to replace the `-x` probe. Scenario: `timing-report.sh` (and any other caller) loses the python3/jq/grep fallback tier and always ends at `unknown` when earlier parsers miss, changing report-tokens/timing workflow classification on real artifacts
- **Proposed resolution**: Replace the `-x` dirname probe with a call to `python3 …/cli.py session read-classification "$f"` (or resolve CLI via `SCRIPT_DIR`/plugin root), swallow stderr, and accept `SIMPLE|HARD` like the current branch; document this explicitly in the call-site cutover section

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-emitter-routing-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:52-58 / scripts/write-session-id.sh:32-44
- **Concern**: Per-verb emitter table lists `write-id` as file-only silent success, but bash uses `emit_kv FAILED/ERROR` on usage errors (fd 3 after `quiet_init`) and raw `echo FAILED/ERROR` on mkdir failure (post-redirect quiet log); verb prose mentions FAILED/ERROR but the routing table omits failure paths. Scenario: A Python port driven by the table alone may drop the failure envelope or route failures to the wrong stream, breaking parity with `write-session-id.sh` and any harness expecting `FAILED=true`/`ERROR=` semantics
- **Proposed resolution**: Add a `write-id` failure row to the emitter table (usage → `emit_kv` on contract fd 3; mkdir failure → same split as bash `echo` after `quiet_init`) and pin it in `test_session_env.py` idempotency/failure cases

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-emitter-routing-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/read-workflow-path.sh:52-54
- **Concern**: After F2 deletes `read-design-classification.sh`, the surviving `[[ -x "$(dirname "$0")/read-design-classification.sh" ]]` guard permanently skips the fallback tier; the plan names `read-workflow-path.sh` in the cutover audit but does not spell out replacing this probe. Scenario: `scripts/timing-report.sh:53` (and any other caller) stops getting `SIMPLE|HARD` from the classification fallback when python3/jq/grep tiers miss, so workflow rows default to `unknown` more often
- **Proposed resolution**: Replace the `-x` bash probe with `python3 …/cli.py session read-classification "$f"` (resolve CLI via `SCRIPT_DIR`/plugin root), keep `2>/dev/null || true`, and accept only `SIMPLE|HARD`; add one line to the call-site cutover bullet for `read-workflow-path.sh`

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-call-site-cutover-gaps
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-finalize.sh:134-192,192-200
- **Concern**: Plan omits implement-finalize integration harness retarget after session CLI cutover. Scenario: After `implement-finalize.sh` stops calling `local-cleanup.sh`, `cleanup-tmpdir.sh`, and `read-session-env-key.sh`, these harnesses still install bash stubs at `$SANDBOX/scripts/{local-cleanup,cleanup-tmpdir,read-session-env-key}.sh`; teardown/postbump will invoke `python3 …/cli.py session …` instead, so assertions on cleanup argv, stall-skip, and token rehydration silently rot
- **Proposed resolution**: Add an explicit plan step to retarget `test-implement-finalize.sh` (and peers below) to stub or fixture the `session` CLI path the cutover script will actually exec

### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-finalize-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:628-631 scripts/cleanup-tmpdir.sh:27-28 plan.txt:23-25 plan.txt:64-65
- **Concern**: [SCOPE-REDUCTION] Single shared cache_sessions_root() cannot satisfy both consumers without picking a semantics winner. Scenario: Plan moves cache_sessions_root into session_env as the sole owner (plan.txt:64-65) while requiring is_allowed_session_tmpdir to match cleanup-tmpdir.sh (plan.txt:23). Today bash uses ${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions (cleanup-tmpdir.sh:27-28) but finalize uses absolute-XDG-only else Path.home()/.cache (finalize.py:628-631). Unifying on either side changes cleanup-tmpdir parity or ship teardown/_tmpdir_under_allowed_root allowlists (ship.py:1051-1058)
- **Proposed resolution**: Keep two explicit helpers in session_env.py (e.g. cleanup_cache_sessions_root mirroring bash expansion vs finalize_cache_sessions_root mirroring finalize.py:628-631) or document one canonical function plus a thin bash-parity wrapper; pin both with targeted pytest cases (relative XDG, empty HOME) before deleting cleanup-tmpdir.sh

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-finalize-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:22-24; scripts/cleanup-tmpdir.sh:31-39; python/finalize.py:740-745
- **Concern**: is_allowed_session_tmpdir omits /private/var/folders while claiming to match the current cleanup/tmpdir allowlist. Scenario: Current cleanup-tmpdir.sh and finalize cleanup validation both accept /private/var/folders. A Python cleanup predicate copied from the plan text would reject resolved macOS temp paths under /private/var/folders, leaving session tmpdirs unremoved.
- **Proposed resolution**: Add /private/var/folders explicitly to the broad cleanup predicate and any shared tmpdir-root helper used for the tmp-family allowlist.

### FINDING_21:
- **Reviewer(s)**: Codex-dyn-finalize-boundary
- **Severity**: latent
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:64-65; python/ship.py:1038-1059
- **Concern**: Plan moves tmpdir path-safety ownership only from finalize.py but misses ship.py's duplicate allowed-root helper. Scenario: After the PR, session_env.py and ship.py would still independently own tmpdir allowed-root logic, so the stated single-owner tmpdir path-safety contract is not achieved and root fixes can diverge.
- **Proposed resolution**: Add an explicit ship.py update: make _tmpdir_under_allowed_root delegate to the new session_env shared allowed-root helper, or remove the duplicate wrapper if callers can use the shared helper directly.

### OOS_1:
- **Description**: [OUT_OF_SCOPE] Cleanup allowlist appears to preserve string-prefix root checks for rm -rf. Scenario: Current matcher accepts paths such as /tmp/../... before removal; this is pre-existing and not required to complete F2, but it is a data-loss hardening candidate
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/cleanup-tmpdir.sh:35-53; plan.txt:22-24,48
- **Phase**: design

### OOS_2:
- **Description**: Stale persist-post-plan-keys.sh listed as approved writer. Scenario: Operators misread which writers remain after F2
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: AGENTS.md:65
- **Phase**: design

### OOS_3:
- **Description**: [OUT_OF_SCOPE] Inlining the full lib-design-tmpdir.sh validator while keeping the bash lib deferred duplicates ~176 lines that ~35 design scripts still source. Scenario: Validator logic can drift from scripts/lib-design-tmpdir.sh until the deferred-lib follow-up lands, causing write-design-env reject/accept to disagree with other design machinery on edge paths
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/session_env.py:27-27
- **Phase**: design

### OOS_4:
- **Description**: [OUT_OF_SCOPE] Linting doc still documents make test-session-env-roundtrip and other harnesses the plan deletes. Scenario: Operators following docs/linting.md hit stale targets until step-7 stale-reference sweep runs
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: docs/linting.md:272-272
- **Phase**: design

### OOS_5:
- **Description**: Plan asserts `entry-gate` success KV is capturable under bash `$(…)` via `quiet_init`+`emit_kv` but only requires generic entry-gate pass/fail tests, not a shell-subprocess capture case mirroring `implement-bootstrap.sh:580-585` or `test_ship.py::test_quiet_init_routes_contract_and_breadcrumb_fds`. Scenario: Shared `logging_util.quiet_init` already has fd-3 coverage in ship tests; duplicate bash-capture test is optional hardening, not required for minimum-change F2
- **Reviewer**: Cursor-dyn-emitter-routing-fidelity
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: plan.txt:50-54 / python/test_session_env.py:74
- **Phase**: design

### OOS_6:
- **Description**: Per-verb emitter table classifies `write-id` as file-only silent success, but bash emits `FAILED=true`/`ERROR=` via `emit_kv` (fd 3) on usage errors and via `echo` (quiet log) on mkdir failure; verb prose mentions FAILED/ERROR but the table omits failure routing. Scenario: Current callers (`implement-bootstrap.sh:699`) ignore stdout and exit code on the happy path, so parity drift is latent unless a future caller captures failure KVs
- **Reviewer**: Cursor-dyn-emitter-routing-fidelity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:57 / scripts/write-session-id.sh:32-44
- **Phase**: design

### OOS_7:
- **Description**: Plan asserts `entry-gate` KV is capturable under bash `gate_out=$(…)` but does not require a shell-subprocess capture test mirroring `implement-bootstrap.sh:580-585`; mitigation is implied via bash analogy only. Scenario: `logging_util.quiet_init` fd-3 behavior is already covered by `python/test_ship.py::test_quiet_init_routes_contract_and_breadcrumb_fds`; risk is regression-only
- **Reviewer**: Cursor-dyn-emitter-routing-fidelity
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: plan.txt:50-54 / python/test_session_env.py:74
- **Phase**: design
