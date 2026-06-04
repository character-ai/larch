# skills/implement/scripts/materialize-manifest-oos.sh — contract

**Consumer**: `step2-implement.sh` on `STATUS=complete` after canonical manifest sanitization, `scripts/ship-pr.sh` `pr-prep` before `run_oos_disposition_gate_if_required_before_oos_pending_false`, and `python/ship.py` before `_oos_gate` when `ctx.manifest_path` is a readable file.

**Contract**: Read `--manifest-path` and `--implement-tmpdir`; use the helper's shared `oos_observations[]` counter (also exposed by `--count-only`) before extracting non-empty observations; merge each non-security observation into `$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md` as `### OOS_N:` blocks. `oos_observations`, when present, must be an array; other types fail closed. Allocation is monotonic `OOS_N`: scan existing `^### OOS_[0-9]+:` headings and append starting at max+1, because title dedup alone is insufficient. Each block carries `title`, `description`, `phase`, `- **Reviewer**: External implementer`, `- **Vote tally**: N/A — auto-filed per policy`, and, when the manifest provided it, `- **focus-area**:`. Structured manifest `focus_area` / `focus-area` is preserved by the dispatcher and treated as a dedicated `- **focus-area**:` field for routing. Exclude only observations whose structured focus-area or description/body contains a dedicated `- **focus-area**:` line whose value begins with `security`; prose such as `focus-area = security` inside Description is retained, and title prefixes alone do not security-route. The helper is idempotent by title, performs no rules-1-2 inline triage, and never calls `/issue`.

**When to load**: Load when editing or invoking the helper; Step 9a.1 itself reads `skills/implement/references/oos-pipeline.md` and treats this helper as the pre-trigger materialization authority.

## Failure semantics

Exit 0 means the manifest had no materializable observations, all observations were already represented by title, or all non-security observations were appended. Exit 1 means usage, missing readable inputs, malformed JSON, `jq` failure, or write failure. Callers fail closed only when the manifest reports a non-empty `oos_observations[]`; otherwise they record a Tool Failures breadcrumb and continue because there is no manifest OOS to lose.

## Makefile and lint wiring

`make test-materialize-manifest-oos` runs `skills/implement/scripts/test-materialize-manifest-oos.sh`.

## Edit-in-sync

When behavior changes, update:

- `skills/implement/scripts/materialize-manifest-oos.sh`.
- `skills/implement/scripts/test-materialize-manifest-oos.sh`.
- `skills/implement/references/oos-pipeline.md` Step 1 materialization pointer.
- `scripts/ship-pr.sh`, `skills/implement/scripts/step2-implement.sh`, and `python/ship.py` invocation sites.
- `scripts/test-implement-structure.sh` pins for monotonic OOS_N and pre-trigger wiring.
