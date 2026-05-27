## Proposed Design Outline

### Goals
- Add a default-off `--allow-findings-outside-tmpdir true|false` flag to `aggregate-findings.sh` that bypasses the containment-under-`--review-tmpdir` check at lines 54–62.
- Preserve all existing `/review` call-site semantics byte-equivalently when the flag is absent or `false` (no behavior change for any current caller).
- Make the rejection self-documenting so operators discover the escape hatch from the failure message itself.

### Non-goals
- No `/review` or `/design` caller wiring; future multi-round-loop callers opt in when their partition lands.
- No relaxation of the symlink rejection at line 50; it stays strict regardless of flag value.
- No audit signal (stderr warning, breadcrumb, warnings.md entry) when relaxation is active — the explicit flag is the audit signal.
- No new file creation; only the three existing files in scope are touched.

### Approach sketch
- Argv parse adds `--allow-findings-outside-tmpdir` with `true|false` grammar matching the sibling `--codex-present` / `--cursor-present` flags; default `false`.
- The containment `case "$_findings_canon"` block becomes flag-gated: when the flag is `true`, the rejection branch short-circuits; the canonicalization itself still runs.
- The symlink-rejection at line 50 stays unconditional and runs before any flag-gated logic.
- The rejection error message gains a hint suffix `(use --allow-findings-outside-tmpdir=true to bypass)` so the escape hatch is discoverable.
- `usage()` updates to list the new optional flag.

### Surfaces in scope
- `skills/review/scripts/aggregate-findings.sh` — argv parse, containment-check gating, usage string, error message.
- `skills/review/scripts/aggregate-findings.md` — sibling doc note describing the new flag and the relaxation contract.
- `skills/review/scripts/test-aggregate-findings.sh` — minimal regression pair: outside-tmpdir allowed under flag, outside-tmpdir rejected without flag.

### Open questions
- None.
