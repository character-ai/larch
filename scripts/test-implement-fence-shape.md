# test-implement-fence-shape.sh

Structural harness for `/implement` prompt Bash fences. It parses `skills/implement/SKILL.md` and fails when a Bash fence contains inline logic instead of a canonical plugin-root prelude plus one repo script invocation.

## Invariants

- Every Bash fence has exactly one plugin-rooted `.sh` / `.py` invocation after allowed source guards, comments, and pre-bootstrap awk fallback lines.
- No adjacent Bash fences are separated only by blank lines.
- Telemetry-only fences (`python3 python/cli.py timing telemetry-mark`, token/timing ledgers, token/timing reports) are banned; wrappers own telemetry internally.
- Inline `session read-key` calls are banned from SKILL.md fences.

## Caller

`make test-implement-fence-shape` and the `test-harnesses-N` shard in `Makefile`.
