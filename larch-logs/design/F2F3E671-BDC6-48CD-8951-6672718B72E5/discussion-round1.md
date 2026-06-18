## Decision 1: Behavioral-parity bar for the port
- **Question**: Should the sh→py port of the launcher/drafter/stderr-tail libs hold strict byte-for-byte behavioral parity, or allow minor normalization?
- **Resolution**: Allow **minor normalization** — low-risk cleanup of obvious bash quirks (dead branches, redundant guards) is permitted **only where observable behavior is unchanged**. Identical external-CLI flags, status-KV contracts, failure classification, and stderr-tail byte caps remain mandatory.
- **Source**: user

## Decision 2: Definition-of-done / deletion completeness
- **Question**: Must issue #4639 fully retire all seven listed libs (cut every consumer + lint clean), or may hard-to-verify libs be deferred?
- **Resolution**: **Full retirement this issue.** All 7 libs deleted; every consumer cut to in-process/`cli.py` (`design_lifecycle.py` drafter dispatch, `checks.py` launcher-lib checks, parity tests, docs); `python/migrated-scripts.tsv` updated; `make lint-retired-scripts` clean. Hard cutover, no shims.
- **Source**: user

## Decision 3: Hard constraint — external-CLI invocation fidelity
- **Question**: What invariant must the port preserve for the spawned vendor CLIs?
- **Resolution**: The ported code MUST invoke the `codex` / `cursor` / `claude` CLIs with byte-identical flags and argv shape. DoD requires running `.claude/rules/verify-external-tool-invocations.md` checks. The drafter status-KV output contract (`launch-codex-drafter.md` / `launch-claude-drafter.md`) and the `lib-failed-agent-stderr-tail` byte-cap / redaction behavior consumed by `collect-results` and the vendor-failure-diagnostics batch must remain compatible.
- **Source**: codebase

## Decision 4: Scope boundary — already-ported overlap
- **Question**: How to treat functions the parent slices (B4 #3673, C1a3 #4167) already ported under Pythonic names in `agents.py`?
- **Resolution**: Verify parity for already-ported pieces (`cursor_auth_preflight`, `cursor_auth_export_env`, transient/quota classification) and port only the genuinely-missing bodies (stderr-tail carrier, drafter launchers, any residual launcher-common helpers). Do not re-port what already has native parity; do consolidate so the sourced libs can be deleted. Target module: `python/agents.py` (extend).
- **Source**: codebase

## Decision 5: Hard constraint — concurrency with in-flight slices
- **Question**: Does the fix surface overlap any in-flight `[IMPLEMENTING]`/`[DESIGNING]` issue?
- **Resolution**: No hard overlap. In-flight `[IMPLEMENTING]` slices #4640 (G11 rendering/round-meta) and #4632 (G3 plan-review loop) are different functional domains. The only shared file is `python/design_lifecycle.py`; G10 touches it only at the drafter-dispatch site (~lines 2234/2251) — keep that edit surgical to minimize rebase risk. No blocked-by edge required (parent slices B4/C1a3 are predecessors, already landed). Lib deletion is self-contained within G10 (remaining bash sourcers are all being deleted in this issue).
- **Source**: codebase

Decisions resolved: 5 (2 user, 3 codebase).
