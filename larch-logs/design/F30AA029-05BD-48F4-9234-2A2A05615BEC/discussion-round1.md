## Decision 1: Item scope — which of the 4 issue items to implement
- **Question**: Issue #3544 lists 4 DX/doc-hardening items for the `/implement` orchestrator. Which should the plan cover?
- **Resolution**: Implement **items 1, 3, and 4**. Item 2 is excluded as already-resolved at repo HEAD (see Decision 3).
- **Source**: user

## Decision 2: Remediation depth for either/or items
- **Question**: For items the issue frames as either/or (item 2 "(a) is cheapest"; item 3 "synopsis and/or example"), how thorough should each fix be?
- **Resolution**: **Cheapest effective per item.** Item 3 → `fail_usage` synopsis only (no SKILL.md literal example). No belt-and-suspenders extras (no `python/ship.py` `--state-file` contract pin).
- **Source**: user

## Decision 3: Item 2 is already resolved at repo HEAD (excluded)
- **Question**: Item 2(a) asks for a literal Python ship `Invoke:` fence mirroring the bash fence, with `--state-file` included. Is it still needed?
- **Resolution**: **Already present at repo HEAD — no work.** The `skills/implement/SKILL.md` Step 8+ unified `Invoke:` fence already has a literal `python3 "${CLAUDE_PLUGIN_ROOT}/python/ship.py"` branch (the `LARCH_SHIP_PR_IMPL` != `bash` arm) that passes `--state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh"` and `--no-logs-commit`; `python/ship.py` `build_parser()` already declares `--state-file`. The issue was filed against the locally-patched 47.0.70 soak copy; the fix landed before 47.0.71. Under "cheapest effective," item 2 has no remaining work. User confirmed: treat as already-resolved (no SKILL.md / ship.py change).
- **Source**: user + codebase

## Decision 4: Hard constraints / non-goals (codebase-derived)
- **Question**: What must this change preserve? What is out of scope?
- **Resolution**:
  - **Item 1**: the self-derive must keep the loud-failure `:?` guard for genuinely broken layouts — derive `CLAUDE_PLUGIN_ROOT` only when unset/empty, then keep the existing `: "${CLAUDE_PLUGIN_ROOT:?…}"` so an empty derivation still aborts.
  - **Item 3**: keep the existing `ERROR=usage: <reason>` line (backward-compatible for any caller/parser) and **add** the synopsis; do not drop the specific reason.
  - **Item 4**: do **not** add `set -euo pipefail` or a shebang at `lib-implement-round-cap.sh` top level — it is a sourced library (`run-step5-review.sh`, `review-and-fix.sh`). Strict mode lives only inside the direct-execution guard block. `count_prior_degraded_rounds` sourcing behavior must be byte-unchanged.
  - **Non-goal**: no behavior change to the ship path (issue's stated scope).
  - **Repo convention**: every touched `.sh` updates its sibling `.md` (`.claude/rules/script-md-siblings.md`); launcher/CLI argv changes need same-PR harness coverage (`.claude/rules/launcher-argv-test-coverage.md`); avoid line numbers / machine-absolute paths in committed prose (`.claude/rules/drift-prone-prose-in-docs.md`).
- **Source**: codebase

---

## Draft remediation direction (non-binding input for Step 1d.7 outline / Step 2b)

Tier: **SIMPLE** — bias to the smallest change per item. This appendix captures the codebase research done in Round 1 so a resumed `/design` re-enters with the analysis intact. It is input, not a finalized plan; Step 2b owns the final plan and Step 3 review may revise it.

### Item 1 — `scripts/implement-bootstrap-invoke.sh` self-derives `CLAUDE_PLUGIN_ROOT`
Root cause: at `/implement` Step 0 *initial* entry the SKILL fence invokes the script while `CLAUDE_PLUGIN_ROOT` is not exported into the Bash-tool env, and both rehydration guards are no-ops (`$IMPLEMENT_TMPDIR` does not exist yet), so the script's `:?` guard hard-fails. The script is always invoked by absolute path inside the plugin tree, so `dirname "$0"/..` is the plugin root.

Insert immediately **before** the existing `: "${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT must be set}"` line (currently the only `CLAUDE_PLUGIN_ROOT` handling, right after MODE validation):

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)" || CLAUDE_PLUGIN_ROOT=""
fi
: "${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT must be set}"
export CLAUDE_PLUGIN_ROOT
```

- Doc: `scripts/implement-bootstrap-invoke.md` — Env inputs table: `CLAUDE_PLUGIN_ROOT` "required" → "self-derived from `$0` when unset; still must resolve to a valid plugin tree (empty derivation preserves the loud `:?` failure)."
- Test: `skills/implement/scripts/test-implement-bootstrap-invoke.sh` — add a case asserting that with `CLAUDE_PLUGIN_ROOT` unset and the script invoked by absolute path (bootstrap child stubbed), it self-derives and does **not** fail at the guard; keep/confirm a broken-layout path still aborts loudly.

### Item 3 — `scripts/append-execution-issue.sh` `fail_usage` prints the synopsis
In `fail_usage()`, after `emit_kv ERROR "usage: $1"`, add a synopsis line:

```bash
emit_kv USAGE "append-execution-issue.sh --log FILE --category CAT (--entry STR | --entry-file FILE)"
```

Keeps `ERROR=` (backward-compatible) and adds a discoverable, labeled synopsis listing the real flags (`--log` / `--category` / `--entry` | `--entry-file`).

- Doc: `scripts/append-execution-issue.md` — Output section: document the new `USAGE=` line emitted on usage failures.
- Test: add `scripts/test-append-execution-issue.sh` (+ sibling `.md` + `Makefile` target `test-append-execution-issue` + a `test-harnesses-*` shard) — there is no harness today. Assert: (a) unknown-flag / missing-required failure emits `FAILED=true` + the `USAGE=` synopsis; (b) a basic happy-path append still succeeds (`APPENDED=true`).

### Item 4 — `scripts/lib-implement-round-cap.sh` gains a direct-exec degraded-count CLI
Append a direct-execution block guarded so sourcing is unaffected (no top-level `set -e`, no shebath change):

```bash
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  set -euo pipefail
  # parse: --count-prior-degraded <IMPLEMENT_TMPDIR> <round>
  # validate round is a positive integer (else usage error, exit 2)
  # print: count_prior_degraded_rounds "$tmpdir" "$round"
fi
```

`count_prior_degraded_rounds(tmpdir, current_round)` counts degraded rounds in `[1, current_round)`. The Step 5 banner runs before the loop, which starts at `--starting-round 1`, so the banner passes round **1** (→ 0 on a fresh run, matching `review-and-fix.sh`'s round-1 inflation; the loop re-reads degraded state each round). Mirrors the `--mode single` runtime usage in `run-step5-review.sh` (passes the round about to execute).

- SKILL site: `skills/implement/SKILL.md` "### Scripted review loop" — the clause "compute `prior_degraded_rounds` the same way `scripts/lib-implement-round-cap.sh` counts prior degraded rounds under `$IMPLEMENT_TMPDIR/round-*/review-and-fix.env`". Replace with an explicit directive to run `bash "${CLAUDE_PLUGIN_ROOT}/scripts/lib-implement-round-cap.sh" --count-prior-degraded "$IMPLEMENT_TMPDIR" 1`, then `round_cap=5; effective_round_cap=$((round_cap + prior_degraded_rounds))`. Banner copy and the `--starting-round 1` fence are otherwise unchanged. Leave the adjacent `dynamic_archetypes_cap` derivation prose alone (out of scope).
- Doc: `scripts/lib-implement-round-cap.md` — add a "## CLI (direct execution)" section: flag, positional args, stdout (single integer), exit codes (0 ok, 2 usage), and the source-vs-exec guard semantics.
- Test: `scripts/test-lib-implement-round-cap.sh` — add CLI assertions: correct count for a tmpdir with N degraded `round-*/review-and-fix.env`, 0 when none, usage error (exit 2) on missing/non-integer round, and that **sourcing** the lib does not trigger the CLI.

### Files-to-touch summary
- `scripts/implement-bootstrap-invoke.sh` + `scripts/implement-bootstrap-invoke.md`
- `skills/implement/scripts/test-implement-bootstrap-invoke.sh`
- `scripts/append-execution-issue.sh` + `scripts/append-execution-issue.md`
- `scripts/test-append-execution-issue.sh` (+ `.md`) + `Makefile` target + `test-harnesses-*` shard
- `scripts/lib-implement-round-cap.sh` + `scripts/lib-implement-round-cap.md`
- `scripts/test-lib-implement-round-cap.sh`
- `skills/implement/SKILL.md` ("### Scripted review loop" banner paragraph only)

### Open items to resolve in Step 2b+
- Confirm the stub style for the item-1 self-derive test (how `test-implement-bootstrap-invoke.sh` stubs the bootstrap child).
- Confirm `Makefile` shard placement for the new `test-append-execution-issue` target and whether a sibling `.md` stub is required.
- Verify the SKILL.md "### Scripted review loop" prose edit does not trip a structure-test grep pin (`scripts/test-implement-structure.sh` had no `prior_degraded` pin in a quick grep — re-confirm before edit).
- Decide whether `USAGE=` (item 3) is the right key name vs. folding the synopsis into the `ERROR=` line; `USAGE=` chosen for backward-compatibility of `ERROR=` parsers.
