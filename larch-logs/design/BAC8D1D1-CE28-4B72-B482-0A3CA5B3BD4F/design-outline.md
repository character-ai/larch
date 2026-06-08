## Proposed Design Outline

### Goals
- One stdlib-only `python/session_env.py` owning session/state lifecycle: session env files, run-params, design current-env, finalize-state, tmpdir resolve + cleanup.
- Hard cutover per the playbook: register `session` verbs in `cli.py`, repoint every `.md`/`.sh` call site, delete the 17 absorbed bash scripts + harnesses + `.md` siblings, lints green.
- Make NEVER #14 an enforced runtime property: an active writer-guard inside the module refuses non-approved session-env writes.

### Non-goals
- No golden bash-parity test module (standard recipe: fresh pytest + one-time retargeted-harness gate, then delete).
- No change to session-env file FORMATS or PPID-keyed naming (`current-design-env-$PPID.sh` preserved verbatim).
- No port of design plan-review/tally state (`persist-retally-step3-env.sh` stays bash); hooks stay bash; no `LARCH_*_IMPL` shims.

### Approach sketch
- New `python/session_env.py`; public writer functions ARE the approved writers; `main(argv)` dispatches `session <verb>`.
- Preserve two emitters: parse-only KEY=VALUE (`session-env.sh`, read via key-reader) and source-safe (`source-env.sh`, `current-design-env-$PPID.sh`, `plugin-root.env`).
- The four `lib-*` scripts become internal module helpers, not CLI verbs; writers/readers/cleanup become verbs.
- Runtime writer-guard validates target path (in-session) + key allowlist before any session-env write.

### Surfaces in scope
- `python/session_env.py`, `python/test_session_env.py`, `python/cli.py` `_REGISTRY`, `python/migrated-scripts.tsv`.
- The 17 absorbed `scripts/*.sh` + `skills/implement/scripts/lib-resolve-implement-tmpdir.sh`, their `.md` + `test-*.sh` siblings.
- ~150 `.md`/`.sh` call sites (session-setup 49, read-session-env-key 47, cleanup-tmpdir 28, …); AGENTS.md NEVER #14 wording.

### Open questions
- CLI domain/verb naming (`session setup|write-env|read-key|cleanup|…`) — settled in the plan/review, not blocking here.
