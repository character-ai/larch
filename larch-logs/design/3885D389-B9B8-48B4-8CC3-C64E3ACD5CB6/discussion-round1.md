## Decision 1: Routing envelope mechanism
- **Question**: How should `implement-bootstrap-invoke.sh` return routing data to the orchestrator after a successful bootstrap?
- **Resolution**: Write `$IMPLEMENT_TMPDIR/bootstrap-routing.env` (file-first) AND emit a compact KV envelope on stdout. The orchestrator parses file-first with a stdout fallback, using a symlink guard and line-by-line parse (no `source`). Matches the `design-route.sh` / `design-publish.sh` / `design-init-runparams.sh` result-env driver pattern.
- **Source**: user

## Decision 2: Wrapper test + contract layout
- **Question**: Where should the wrapper's regression tests live?
- **Resolution**: New dedicated `skills/implement/scripts/test-implement-bootstrap-invoke.sh` with its own Makefile target, covering the envelope, both invocation modes (initial `--up-to-phase coder` / resume `--up-to-phase plan --resume-plan-tail`), and exit-2 messaging. Add the mandatory `scripts/implement-bootstrap-invoke.md` contract sibling regardless.
- **Source**: user

## Decision 3: Sanctioned session-env writers (hard constraint)
- **Question**: May the wrapper write or append `session-env.sh`?
- **Resolution**: No (NEVER #14, #2326-adjacent). The wrapper only runs `implement-bootstrap.sh`, which already uses the sanctioned writers (`write-session-env.sh` / `session-setup.sh` / `persist-implement-run-flags.sh`). The wrapper must not write or append `session-env.sh` itself.
- **Source**: codebase (issue + AGENTS.md NEVER #14)

## Decision 4: Preserve exit-2 operator strings + redaction (hard constraint)
- **Question**: Can the exit-2 operator messages or stderr redaction change?
- **Resolution**: No. Move the exact per-`STEP_FAILED` operator strings verbatim into the wrapper, including the `copy-plan` / `gh-issue-view` stderr redaction pipe (`redact-secrets.sh` | `redact-tmpdir-paths.sh`). The wrapper prints the message and propagates exit 2; the orchestrator only relays the exit.
- **Source**: codebase (issue)

## Decision 5: Preserve dirty-tree resume routing semantics (hard constraint)
- **Question**: Can resume-tail behavior change?
- **Resolution**: No. Both the initial (`--up-to-phase coder`) and the dirty-tree resume (`--up-to-phase plan --resume-plan-tail`) invocations run through ONE wrapper code path (a mode arg selects phase/resume/coder differences). The resume tail reuses persisted Step 0 availability keys from `session-env.sh`; no fresh reviewer probes.
- **Source**: codebase (issue)

## Decision 6: Envelope key set must cover the Degraded-tools gate
- **Question**: Is the "~8 routing keys" set sufficient, given the immediate post-Step-0 consumers?
- **Resolution**: The envelope must also carry `IMPLEMENT_TMPDIR` and the four presence keys the Degraded-tools gate reads "from the bootstrap parse above" (`CODEX_PRESENT`, `CURSOR_PRESENT`, `CODEX_BINARY_FOUND`, `CURSOR_BINARY_FOUND`), so the gate keeps working without extra `read-session-env-key.sh` calls. Exact final key set is fixed in the plan against the routing table + degraded gate + dirty-tree recovery consumers.
- **Source**: codebase (SKILL.md Step 0 routing table + degraded-tools gate)

## Decision 7: Doc-hygiene rider (in-scope)
- **Question**: Is the `codex-manifest-schema.md` "When to load" fix in scope for this same design?
- **Resolution**: Yes. Retarget the "When to load" line to the real consumers (`step2-implement.sh`, `ship-pr.sh`, `codex-implementer.md` / `cursor-implementer.md`) and drop the phantom "SKILL.md MANDATORY directive at Step 2 entry" claim. ~1–2 lines, no behavioral change.
- **Source**: codebase (issue rider)

## Non-goals
- Do NOT change `implement-bootstrap.sh` behavior or its KV output contract.
- Do NOT change `/implement` routing semantics or any step beyond Step 0.
- Do NOT touch the Python `ship-pr.sh` rework tree.
