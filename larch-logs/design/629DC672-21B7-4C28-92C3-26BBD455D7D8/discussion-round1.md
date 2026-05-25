## Decision 1: emit_breadcrumb migration scope
- **Question**: How wide should item 3 (emit_breadcrumb --category= migration) be?
- **Resolution**: Only stream-relevant callsites (callers that actually execute when LARCH_BREADCRUMB_STREAM is set — i.e., calls inside Family B scripts already wired with done-traps plus their helpers). Skip cleanup, upgrade-larch, report-tokens and similar single-shot CLIs where the stream is never set.
- **Source**: user

## Decision 2: Treatment of already-complete items
- **Question**: How should already-complete items (item 1 done-traps, item 9 foreground cleanup) be treated in the plan?
- **Resolution**: Skip them entirely. Mention them in a "Context — already complete" section so reviewers know we audited them, but write no implementation steps for items 1 and 9.
- **Source**: user

## Decision 3: Legacy backward compatibility for emit_breadcrumb
- **Question**: Do callers without --category= keep working in legacy mode (no stream), or must --category= become mandatory?
- **Resolution**: Keep legacy mode untouched — `emit_breadcrumb TEXT` without --category= still works when LARCH_BREADCRUMB_STREAM is unset (current code behavior). Only stream-active callers need migration. The function already prints `WARN unknown-category=<missing>` when the stream is set and category is missing, then drops from stream; that's the intended degraded-mode contract.
- **Source**: codebase (scripts/lib-quiet.sh emit_breadcrumb body)

## Decision 4: Fixed category vocabulary scope
- **Question**: What is the authoritative vocabulary list for emit_breadcrumb --category=?
- **Resolution**: `progress, warn, stall, retry, escalate, wait-ci, network-flake` — enforced by `larch_quiet_bc_valid_category()` in scripts/lib-quiet.sh. The issue body lists this same set explicitly.
- **Source**: codebase (scripts/lib-quiet.sh:larch_quiet_bc_valid_category)
