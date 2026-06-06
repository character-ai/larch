## Goal
Implement issue #3544: [IMPLEMENTING] [BUG] (URGENT) Reduce /implement orchestrator friction: 4 gaps surfaced by #3448 soak run\n\n## Context.

## Implementation Plan
## Plan

Three additive DX/doc-hardening fixes from the #3448 soak run. SIMPLE tier: cheapest effective change per item, no behavior change to the ship path. Item 2 is excluded — already resolved at repo HEAD (the unified Step 8+ `Invoke:` fence already has a literal `python3 .../python/ship.py` branch passing `--state-file`).

### Item 1 — `implement-bootstrap-invoke.sh` self-derives `CLAUDE_PLUGIN_ROOT`

Wrapper-only (no `skills/implement/SKILL.md` Step 0 edit). The Step 0 fence invokes the wrapper by a loader-expanded absolute path, so `$0` is absolute and the self-derive fixes the wrapper's own `:?` guard; `parse-bootstrap-routing-envelope.sh` has no `CLAUDE_PLUGIN_ROOT` dependency, so the parent shell needs no rehydration.

**UPDATED: `scripts/implement-bootstrap-invoke.sh`** — immediately before the existing `: "${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT must be set}"` line, insert:

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)" || CLAUDE_PLUGIN_ROOT=""
fi
: "${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT must be set}"
export CLAUDE_PLUGIN_ROOT
```

`set -e` safe: the `|| CLAUDE_PLUGIN_ROOT=""` arm absorbs a failed `cd`; an empty derivation still aborts at the unchanged guard. `export` reaches the `implement-bootstrap.sh` child.

**UPDATED: `scripts/implement-bootstrap-invoke.md`** — in the env-inputs table, note `CLAUDE_PLUGIN_ROOT` is self-derived from `$0` when unset, exported to the child, still guarded with `:?`. Sole documentation site for the self-derive.

**UPDATED: `skills/implement/scripts/test-implement-bootstrap-invoke.sh`** — add a sandbox case that invokes the wrapper by absolute path with `env -u CLAUDE_PLUGIN_ROOT` (not via `run_wrapper`, which exports the var); assert rc 0, normal routing envelope, bootstrap stub reached, stub observes a non-empty derived `CLAUDE_PLUGIN_ROOT`. Keep existing usage/exit cases.

### Item 3 — `append-execution-issue.sh` `fail_usage` prints a `USAGE=` synopsis

**UPDATED: `scripts/append-execution-issue.sh`** — in `fail_usage()`, after `emit_kv ERROR "usage: $1"` and before `exit 1`, add:

```bash
emit_kv USAGE "append-execution-issue.sh --log FILE --category CAT (--entry STR | --entry-file FILE)"
```

Keeps `FAILED=true` and the specific `ERROR=usage:` line. Only the `fail_usage` class (exit 1) changes; exit-2 I/O failures are unchanged.

**UPDATED: `scripts/append-execution-issue.md`** — in "Output", document the `USAGE=` synopsis line emitted on `fail_usage`-class errors, with the three-line failure envelope.

**NEW: `scripts/test-append-execution-issue.sh`** — offline harness (no harness exists today). `REPO_ROOT` from `BASH_SOURCE`, `mktemp -d` sandbox + EXIT cleanup, `LARCH_QUIET_DISABLE=1`, PASS/FAIL counters. Assert: unknown flag emits `FAILED=true` + `ERROR=usage:` + `USAGE=` and exits 1; missing `--category` emits the `USAGE=` synopsis and exits 1; happy path appends under `### Warnings`, emits `APPENDED=true`, exits 0. Bash 3.2 compatible.

**NEW: `scripts/test-append-execution-issue.md`** — sibling stub naming the harness, primary `scripts/append-execution-issue.sh`, and `make test-append-execution-issue`.

**UPDATED: `agent-lint.toml`** — add `scripts/test-append-execution-issue.sh` and `scripts/test-append-execution-issue.md` to the dead-script exclude list beside the existing `scripts/test-append-tool-failure.sh` / `.md` entries, with the same Makefile-only rationale (agent-lint does not treat Makefile targets as reachability edges).

### Item 4 — `lib-implement-round-cap.sh` direct-exec degraded-count CLI

**UPDATED: `scripts/lib-implement-round-cap.sh`** — append a direct-execution block; keep the existing shebang and `count_prior_degraded_rounds` sourcing behavior byte-unchanged; no top-level `set -euo pipefail`.

```bash
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  set -euo pipefail
  _lib_round_cap_usage() {
    printf 'usage: lib-implement-round-cap.sh --count-prior-degraded <IMPLEMENT_TMPDIR> <current_round>\n' >&2
    exit 2
  }
  case "${1:-}" in
    --count-prior-degraded)
      [ "$#" -eq 3 ] || _lib_round_cap_usage
      case "$3" in
        ''|*[!0-9]*) _lib_round_cap_usage ;;
      esac
      [ "$3" -ge 1 ] || _lib_round_cap_usage
      count_prior_degraded_rounds "$2" "$3"
      ;;
    *)
      _lib_round_cap_usage
      ;;
  esac
fi
```

Prints `count_prior_degraded_rounds` for the round (banner passes round 1 → 0 on a fresh run). Non-positive / non-integer round → usage error exit 2. Bash 3.2 compatible.

**UPDATED: `scripts/lib-implement-round-cap.md`** — add a "## CLI (direct execution)" section: flag, positional args, stdout (single integer), exit codes (0 ok, 2 usage), source-vs-exec guard.

**UPDATED: `scripts/test-lib-implement-round-cap.sh`** — keep sourced-function cases; add CLI assertions executing the lib by path: correct count with N degraded rounds, 0 for fresh round 1, exit 2 on missing arg and non-integer/non-positive round, and that sourcing reaches the function cases without exiting.

**NEW: `scripts/test-lib-implement-round-cap.md`** — sibling stub (the harness currently has none) naming `scripts/lib-implement-round-cap.sh` as primary and `make test-lib-implement-round-cap`.

**UPDATED: `skills/implement/SKILL.md`** — Step 5 "### Scripted review loop" only. Replace the clause that tells the orchestrator to compute `prior_degraded_rounds` "the same way `scripts/lib-implement-round-cap.sh` counts prior degraded rounds under `$IMPLEMENT_TMPDIR/round-*/review-and-fix.env`" with a directive to run `${CLAUDE_PLUGIN_ROOT}/scripts/lib-implement-round-cap.sh --count-prior-degraded "$IMPLEMENT_TMPDIR" 1` and use its stdout. Leave `round_cap=5`, `effective_round_cap`, the `dynamic_archetypes_cap` derivation, and the banner template unchanged. Do **not** add a new Bash fence or restructure existing Step 5 fences (keeps `test-implement-timing-rehydration.sh` guard counts unchanged). No line-number or machine-path prose.

**UPDATED: `Makefile`** — add a `test-append-execution-issue` target mirroring siblings (`bash scripts/harness-timer.sh $@ bash scripts/test-append-execution-issue.sh`), add it to `.PHONY`, and to one `test-harnesses-N` shard so `test-harness-shards-coverage` stays green.

### Edge cases and failure modes

- Item 1: failed `cd` → empty value → unchanged `:?` abort; an already-set value is left untouched.
- Item 3: `USAGE=` added only on the `fail_usage` (exit 1) class; exit-2 I/O errors keep their two-line output.
- Item 4: round 0 / non-numeric → exit 2; round 1 → 0; sourcing must stay inert (a malformed guard would `exit 2` at source and break the Step 5 loop).

## Acceptance

- [ ] `scripts/implement-bootstrap-invoke.sh` self-derives and exports `CLAUDE_PLUGIN_ROOT` from `$0` when unset; an empty derivation still aborts at the `:?` guard. `make test-implement-bootstrap-invoke` green, including a new `env -u CLAUDE_PLUGIN_ROOT` direct-wrapper case; no `skills/implement/SKILL.md` Step 0 edit.
- [ ] `scripts/append-execution-issue.sh` `fail_usage` emits a `USAGE=` synopsis line alongside the unchanged `FAILED=true` / `ERROR=usage:` lines and exits 1; the happy path still emits `APPENDED=true`. New `scripts/test-append-execution-issue.sh` + sibling `.md` exist and `make test-append-execution-issue` is green; `agent-lint.toml` excludes the new harness.
- [ ] `scripts/lib-implement-round-cap.sh --count-prior-degraded <tmpdir> <round>` prints the integer count (exit 0), rejects missing/non-positive/non-integer round (exit 2), and sourcing the lib never triggers the CLI. `make test-lib-implement-round-cap` green; sibling `scripts/test-lib-implement-round-cap.md` exists.
- [ ] `skills/implement/SKILL.md` Step 5 banner directs the orchestrator to the CLI instead of a glob/loop algorithm, with no new/restructured Bash fence; `make test-implement-timing-rehydration` and `make test-implement-structure` stay green.
- [ ] `Makefile` registers `test-append-execution-issue` (`.PHONY` + a shard); `make test-harness-shards-coverage` green.
- [ ] `bash scripts/relevant-checks.sh` passes (shellcheck, markdownlint, bash32, sibling-`.md`, agent-lint). No behavior change to the ship path.

diff_lines: 164

## Test plan
(no test plan section in plan-file)
