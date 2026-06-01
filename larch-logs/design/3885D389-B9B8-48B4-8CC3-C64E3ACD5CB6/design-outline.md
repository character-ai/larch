## Proposed Design Outline

### Goals
- Extract the `/implement` Step 0 inline bootstrap harness into one `scripts/implement-bootstrap-invoke.sh` wrapper; collapse the duplicated initial and dirty-tree-resume copies into a single code path.
- Remove the dead `_ib_parse_bootstrap_out` helper and fix the routing-table prose that still names it as the resume mechanism.
- Rider: fix the `codex-manifest-schema.md` "When to load" line to point at its real consumers.

### Non-goals
- No change to `implement-bootstrap.sh` behavior or its KV output contract.
- No change to `/implement` routing semantics or any step beyond Step 0.
- No edits to the `python/` `ship-pr.sh` rework tree.

### Approach sketch
- New `scripts/implement-bootstrap-invoke.sh`: assembles bootstrap args from exported env, then runs `implement-bootstrap.sh` for both modes through one path — `--mode initial` (`--up-to-phase coder`, passes `--coder`) and `--mode resume` (`--up-to-phase plan --resume-plan-tail`, no `--coder`).
- On exit 2: wrapper prints the exact per-`STEP_FAILED` operator message with the `copy-plan` / `gh-issue-view` stderr redaction (`redact-secrets.sh` | `redact-tmpdir-paths.sh`), then propagates exit 2.
- On success: wrapper writes `$IMPLEMENT_TMPDIR/bootstrap-routing.env` (file-first) and echoes the compact KV envelope on stdout — routing keys + `IMPLEMENT_TMPDIR` + the four Degraded-tools-gate presence keys.
- `SKILL.md` Step 0 shrinks to two thin call sites (initial + resume) that share one routing-env parse block (file-first, stdout fallback, symlink-guarded; no `source`).
- The wrapper never writes `session-env.sh` (NEVER #14); the bootstrap's sanctioned writers still own that file.

### Surfaces in scope
- `scripts/implement-bootstrap-invoke.sh` + `scripts/implement-bootstrap-invoke.md` (new)
- `skills/implement/SKILL.md` — Step 0 region only (initial + resume blocks, routing-table prose)
- `skills/implement/scripts/test-implement-bootstrap-invoke.sh` + `.md`; `Makefile` test target (new)
- `skills/implement/references/codex-manifest-schema.md` (rider, ~1-2 lines)

### Open questions
- None. Envelope mechanism (env file + stdout fallback) and test layout (dedicated harness) were resolved in Round 1.
