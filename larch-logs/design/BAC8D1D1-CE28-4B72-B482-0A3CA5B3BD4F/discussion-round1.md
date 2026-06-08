## Decision 1: Scope of absorbed scripts
- **Question**: Absorb all 17 listed bash scripts, or defer the two git-branch-lifecycle ones (local-cleanup.sh, session-entry-gate.sh) to sibling B1 (#3670)?
- **Resolution**: Absorb all 17 as listed in the issue. F2's module gains the two git-lifecycle verbs; no re-scoping of B1.
- **Source**: user

## Decision 2: Parity-testing rigor (Definition of Done)
- **Question**: Add golden bash-parity tests for the file-emitting writers, or use the standard playbook recipe only?
- **Resolution**: Standard recipe only — fresh colocated pytest plus the one-time retargeted-harness parity gate (playbook step 5) before deleting bash. No dedicated test_session_env_bash_parity.py golden module.
- **Source**: user

## Decision 3: NEVER #14 enforcement mechanism
- **Question**: Make "session-env writable only by approved writers" a convention (public API + existing guards) or an active runtime writer-guard?
- **Resolution**: Active runtime writer-guard. The module actively validates/refuses session-env writes from non-approved callers at runtime. Note: NEVER #14 has NO dedicated lint/hook enforcement today (convention + review only) — this guard is net-new enforcement.
- **Source**: user

## Decision 4: "sibling persist-* session writers" enumeration
- **Question**: Which exact persist-* scripts does the issue's "and sibling persist-* session writers" phrase cover?
- **Resolution**: Only scripts/persist-implement-run-flags.sh exists under scripts/. skills/design/scripts/persist-retally-step3-env.sh is design plan-review/tally state, NOT session/state — out of F2 scope (belongs with the design-review migration issues). No hidden persist-* set.
- **Source**: codebase

## Decision 5: Dual read mechanisms must be preserved
- **Question**: Do all absorbed state files share one read mechanism?
- **Resolution**: No. The /implement session-env.sh is parse-only (KEY=VALUE, values NOT shell-quoted; read via read-session-env-key.sh). The /design source-env.sh and current-design-env-$PPID.sh ARE shell-`source`d by bash .md preludes. The port MUST preserve both: a parse-only emitter and a source-safe emitter. PPID-keyed current-design-env naming (current-design-env-$PPID.sh) must be preserved verbatim.
- **Source**: codebase

## Decision 6: Cutover surface is .md/.sh only
- **Question**: Do any Python modules invoke the absorbed scripts (cross-language cutover)?
- **Resolution**: No Python module shells out to the absorbed scripts. Cutover repoints only skill .md files and surviving bash scripts to direct `python3 cli.py session <verb>` calls. Surface is large (session-setup.sh in 49 files, read-session-env-key.sh in 47, cleanup-tmpdir.sh in 28).
- **Source**: codebase

## Decision 7: Hard cutover in one change (playbook)
- **Question**: Phased cutover or single-commit hard cutover?
- **Resolution**: Single-change hard cutover per docs/python-migration.md — port functions, register CLI verbs, cut ALL consumers, run retargeted harnesses once as a parity gate, delete bash + harness + .md siblings, append to migrated-scripts.tsv, lint-retired-scripts green. No shims, no LARCH_*_IMPL selectors.
- **Source**: codebase / playbook
