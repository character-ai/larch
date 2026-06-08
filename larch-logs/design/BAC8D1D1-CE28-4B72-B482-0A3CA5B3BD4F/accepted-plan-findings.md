### FINDING_1: Writer-target validator must use XDG-aware cache sessions root
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: Predicate 2 for approved session-env writes risks hardcoding `~/.cache/larch/sessions` even though session setup can create session tmpdirs under `$XDG_CACHE_HOME/larch/sessions`; valid write-env / persist / restore writes would then be rejected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In predicate 2 spell out reuse of moved cache_sessions_root() (same logic as scripts/session-setup.sh session_cache_root); add test_session_env.py case with XDG_CACHE_HOME set asserting writer-guard accepts session file writes under XDG sessions root while symlink stays under ~/.cache/larch/sessions
  - From Cursor-Innovation: Document predicate (2) uses XDG-aware cache_sessions_root() matching session-setup.sh and cleanup-tmpdir.sh; reserve hardcoded ~/.cache only for the design-env symlink validator


### FINDING_2: Writer guard conflicts with surviving `--write-session-env` harness outputs
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The proposed strict writer-target validator only accepts real `claude-*` session dirs, but surviving setup callers and lint harnesses still write `session-env.sh` to arbitrary `/tmp` paths or custom prefixes; cutover could break make lint or force ad hoc guard weakening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the cutover plan for these surviving callers: use accepted claude-* prefixes and place --write-session-env outputs under an allowed claude-* temp/session directory, or make session setup write to its freshly created SESSION_TMPDIR/session-env.sh
  - From Codex-Innovation: Retarget these surviving harnesses during call-site cutover: use the session CLI and place written session-env files under validator-accepted claude-review/claude-implement temp dirs, or explicitly include equivalent harness rewrites in the plan
  - From Cursor-Pragmatic: Scope the prefix check to the session tmpdir created by setup (or to $IMPLEMENT_TMPDIR/session-env.sh / plugin-root.env writes); for setup --write-session-env allow broad /tmp|cache-root containment only, matching current bash which validates values but not output dirname prefix
  - From Codex-Pragmatic: Amend the plan to either validate setup-owned writes against the freshly created session tmpdir/prefix contract or explicitly retarget these surviving harnesses to allowed claude session output paths before enabling the guard


### FINDING_3: Missing raw finalize-state parity coverage for shell metacharacters
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The plan lacks a parity test ensuring `restore-finalize-state` reads ship-pr-state values as raw RHS text; if it reuses shlex parsing, values containing quotes, `$()`, or embedded `=` can be corrupted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add an explicit pytest (and retargeted harness case) with ship-pr-state fixtures like `PR_TITLE=Implement $(echo x)=y` asserting byte-identical round-trip via the dedicated raw reader only


### FINDING_7: Missing pytest coverage for `--run-id` / `LARCH_RUN_ID`
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The proposed pytest replacement omits `test-session-env-roundtrip.sh` H.* coverage for `--run-id` and `LARCH_RUN_ID`, leaving bootstrap run-id persistence regressions unguarded after harness deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add explicit pytest cases for valid `--run-id` → `LARCH_RUN_ID` round-trip, invalid run-id rejection, and absent `--run-id` omitting the key (port H.1–H.4 from `scripts/test-session-env-roundtrip.sh`)


### FINDING_9: `write-id` emitter table omits failure-path parity
- **Reviewer(s)**: Cursor-dyn-emitter-routing-fidelity
- **Severity**: important
- **Concern**: The per-verb emitter table marks `write-id` as file-only silent success but does not encode current `FAILED=true` / `ERROR=` behavior for usage and mkdir failures, risking wrong failure envelopes or streams in the Python port.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-emitter-routing-fidelity: Add a `write-id` failure row to the emitter table (usage → `emit_kv` on contract fd 3; mkdir failure → same split as bash `echo` after `quiet_init`) and pin it in `test_session_env.py` idempotency/failure cases


### FINDING_11: Tmpdir allowlist omits `/private/var/folders`
- **Reviewer(s)**: Codex-dyn-finalize-boundary
- **Severity**: important
- **Concern**: The planned shared tmpdir predicate claims to match current cleanup/finalize behavior but omits `/private/var/folders`, so resolved macOS temp paths could be rejected and left unremoved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-finalize-boundary: Add /private/var/folders explicitly to the broad cleanup predicate and any shared tmpdir-root helper used for the tmp-family allowlist.


### FINDING_13:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-skill-md-flag-signature.sh:74-91; scripts/test-lint-skill-md-flag-signature.sh:121-146; plan.txt:86
- **Concern**: [SCOPE-REDUCTION] Plan retargets shell-only flag-signature fixtures to python/cli.py without changing the linter resolver. Scenario: The resolver only inspects */scripts/*.sh tokens, so a fixture using python3 .../cli.py session write-run-params is ignored; existing assert_lint_fails_for cases then fail or lose verification, blocking make lint
- **Proposed resolution**: Do not point this shell-linter fixture at the Python CLI unless the linter gains a session-verb metadata source; minimum-change fix is to replace the retired write-run-params fixture with a non-retired shell fixture and cover write-run-params flags in test_session_env.py


### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-finalize-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:628-631 scripts/cleanup-tmpdir.sh:27-28 plan.txt:23-25 plan.txt:64-65
- **Concern**: [SCOPE-REDUCTION] Single shared cache_sessions_root() cannot satisfy both consumers without picking a semantics winner. Scenario: Plan moves cache_sessions_root into session_env as the sole owner (plan.txt:64-65) while requiring is_allowed_session_tmpdir to match cleanup-tmpdir.sh (plan.txt:23). Today bash uses ${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions (cleanup-tmpdir.sh:27-28) but finalize uses absolute-XDG-only else Path.home()/.cache (finalize.py:628-631). Unifying on either side changes cleanup-tmpdir parity or ship teardown/_tmpdir_under_allowed_root allowlists (ship.py:1051-1058)
- **Proposed resolution**: Keep two explicit helpers in session_env.py (e.g. cleanup_cache_sessions_root mirroring bash expansion vs finalize_cache_sessions_root mirroring finalize.py:628-631) or document one canonical function plus a thin bash-parity wrapper; pin both with targeted pytest cases (relative XDG, empty HOME) before deleting cleanup-tmpdir.sh


