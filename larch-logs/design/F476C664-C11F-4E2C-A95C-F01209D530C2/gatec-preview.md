## Final Design Plan

## Plan

## Approach

Extract changed symbols from fix diffs, find external consumers, and include them in bundle evidence. Make every required evidence scan status-aware so a command failure cannot be represented as empty evidence or certify a fix. Widen later-history and revert scans to successfully resolved consumer paths. Evolve agent and ledger schemas additively, retain stage-specific evidence, and distinguish an instance verdict from class completeness. Render verified introduced risks and only confirmed-instance class-open findings without changing approval-gated filing.

### UPDATED: python/larch/issue/analyze_bugs.py

- Replace empty-output-on-error handling for required diff, consumer, later-history, and revert scans with structured results that preserve status, stdout, and a bounded failure reason. Treat grep exit `1` as a successful no-match result; treat invalid checkouts, other grep exits, and failed Git commands as scan failures.
- Parse added and deleted diff-hunk lines for function or method definitions, dataclass-style fields, and string-literal dictionary keys. Deduplicate stable symbol names. If diff extraction fails, record that failure rather than treating the symbol set as empty.
- Search the evidence checkout for symbol references outside touched files. Record deterministic `path:line` entries and tag shell, skill Markdown, and hook consumers as `cross-language`.
- Add persisted per-bundle scan state for diff extraction, consumer discovery, later-history, and revert evidence, including bounded reasons. Render a non-empty failure stanza and explicit status in bundle Markdown when a scan fails; render an empty consumer result only for a successful no-match scan.
- On a consumer or diff-discovery failure, use touched files only for best-effort diagnostic history/revert scans, mark the widened evidence incomplete, and ensure those diagnostic results cannot restore certification.
- Build `all_scan_files` from touched files plus successfully discovered consumer paths. Use it for later-history and revert scans while keeping `touched_files` unchanged for existing analytics.
- Include the ordered widened file set and scan-status/error sentinel in `later_history_hash`, or bypass cached certification evidence when scans are incomplete, so old or successful cache entries cannot mask failed current scans. This causes the intended one-time cache invalidation for successful widened scans.
- Propagate incomplete required-evidence status through bundle coordination, ingest, and `_final_verdict_with_tier`: use the existing mechanical `NEEDS_DEEP` path before deep review and reject or downgrade any `FIXED_CLEAR`, `FIXED_LIKELY`, or `CONFIRMED_FIXED` claim while required evidence remains incomplete.
- Add stage-specific `introduced_risk` and evidence-reason fields, plus `class_complete`, `sibling_sites`, and `legacy_schema`, to ingest and ledger records.
- Accept exactly the prior or current triage and verifier key sets. Mark prior shapes as `legacy_schema=true`; reject partial, mixed, or extra-key shapes.
- Validate current triage and verifier `introduced_risk` values as non-empty strings: `none found` is the exact no-risk sentinel; any other value is a risk claim and requires a non-empty introduced-risk evidence reason. Reject malformed or incoherent current rows instead of defaulting them.
- For current verifier rows, validate `class_complete` as a boolean and `sibling_sites` as valid `path:symbol` strings. For `CONFIRMED_FIXED`, require non-empty sibling sites when `class_complete=false`; require an empty sibling list when `class_complete=true`. For non-confirmed instance verdicts, permit `class_complete=false` with an empty list so fail-closed verifier results remain ingestible.
- Detect persisted records missing current fields during ledger loading and mark them legacy rather than defaulting them into current claims.
- Preserve new fields and their originating stage through ledger serialization and loading. On refreshed triage, clear all invalidated deep-stage risk, class-completeness, sibling-site, and evidence fields rather than retaining stale deep data.
- Render `## Introduced risk` only for non-legacy rows with a present selected-stage risk other than `none found`: prefer completed deep-stage risk and its evidence reason, otherwise use valid triage-stage risk and its evidence reason.
- Render `## Instance fixed, class open` only for non-legacy rows with completed current-schema verifier output, an instance verdict of `CONFIRMED_FIXED`, `class_complete=false`, and non-empty validated sibling sites.
- Build the follow-up body from terminal-verdict follow-ups plus those eligible confirmed-instance class-open rows. Write `follow-up-issue.md` when either set is non-empty, while preserving the existing approval-gated filing path.

### UPDATED: .claude/agents/bug-fix-triage.md

- Require `introduced_risk` and its evidence-reason field in the current strict JSONL schema.
- Tell the agent to name the most plausible consumer defect or emit exactly `none found`, with a non-empty evidence sentence tied to bundle evidence.
- Require failed scan-status evidence to be treated as insufficient for a clear or likely-fixed conclusion.
- Preserve strict JSONL, evidence-token, unreadable-evidence, and exact-key rules.

### UPDATED: .claude/agents/bug-fix-verifier.md

- Require `introduced_risk`, its evidence-reason field, `class_complete`, and `sibling_sites`.
- Require a targeted Grep against the current checkout for every introduced-risk verdict, including `none found`.
- Require at least one targeted Grep outside the fix before `class_complete=true`.
- Define the instance verdict and class completeness independently: `CONFIRMED_FIXED` plus `class_complete=false` requires listed `path:symbol` siblings; non-confirmed verdicts may use an empty sibling list when class completeness cannot be established.
- Require an empty sibling list when `class_complete=true`.
- Require failed bundle scan status, checkout failures, Grep failures, or insufficient search evidence to produce a fail-closed outcome rather than a certified instance verdict.
- Preserve read-only operation and strict JSONL output.

### UPDATED: .claude/skills/analyze-bugs/SKILL.md

- Document consumer evidence included in bundles, explicit scan-status failure stanzas, and that diff, consumer, history, or revert scan failures block clear, likely, and confirmed-fixed certification.
- Note that widening `later_history_hash` invalidates existing successful cache entries once and that incomplete scans cannot reuse cached certification evidence.
- Describe stage-specific risk precedence, legacy-row suppression, instance-verdict/class-completeness separation, both report sections, and confirmed-instance-only class-open follow-up behavior.

### UPDATED: python/tests/issue/test_analyze_bugs.py

- Add symbol extraction and consumer-scan coverage for Python definitions, dataclass field renames, and string dictionary keys.
- Reproduce the #6946 shape: a Python field rename with stale shell and SKILL.md consumers. Assert cross-language tags, exclusion of touched files, a non-none verifier introduced-risk fixture, and targeted checkout-Grep contract text.
- Verify consumer paths widen later-history, revert-scan, and hash inputs.
- Cover successful no-match grep exit `1` separately from failed grep, failed diff extraction, invalid checkout, failed later-history, and failed revert scans. Assert persisted failure status and bundle error stanzas, `NEEDS_DEEP`/non-certification coordination, cache non-reuse, and no clear, likely, or confirmed-fixed verdict from incomplete evidence.
- Cover exact current schemas, accepted legacy schemas, legacy marking during ingest and persisted-ledger loading, and rejection of partial, mixed, extra-key, malformed, empty, or incoherent current rows.
- Add current-triage tests rejecting invalid `introduced_risk` values and missing risk evidence reasons while confirming prior triage rows ingest as legacy.
- Verify `CONFIRMED_FIXED` plus `class_complete=false` requires valid non-empty `path:symbol` sibling sites, `class_complete=true` requires an empty sibling list, and non-confirmed fail-closed verifier verdicts can use `class_complete=false` with an empty list.
- Add the #6632-shaped end-to-end fixture: duplicate the same regex or pattern in two modules, fix only one module, ingest a `CONFIRMED_FIXED` verifier result with `class_complete=false` and the other module’s sibling site, then assert class-open report and follow-up eligibility.
- Verify non-confirmed instance rows, including rows with sibling data, never render as `Instance fixed, class open` and never enter class-open follow-ups.
- Verify ledger round trips retain stage-specific risk provenance and triage refresh clears stale deep risk and class data.
- Add verifier-contract assertions for targeted risk Grep, class-completeness Grep, failed-scan handling, and the required new fields.
- Add report fixture coverage for triage-only and deep-stage risk precedence, legacy suppression, one introduced-risk row, one eligible class-open row, and class-open-only follow-up body generation.

## Edge cases

- Diffs without recognized symbols produce an empty consumer section only after successful extraction and retain touched-file-only scans.
- Failed diff or consumer discovery emits explicit incomplete-evidence status, not an empty blast radius.
- Deleted names remain searchable so stale consumers of renamed fields are visible.
- Multiple symbols or references on one line remain deduplicated and deterministic.
- References inside touched files do not become consumers.
- Legacy rows remain usable but cannot render introduced-risk or class-completeness claims.
- `none found` risks stay out of alert sections and follow-up content.
- A non-confirmed instance verdict cannot be reported as fixed merely because its class is incomplete.
- Consumer scan errors do not imply an empty blast radius.

## Failure modes

- Reject malformed current-version agent rows rather than silently dropping or defaulting fields.
- Do not collapse required command failures into empty diff, consumer, history, or revert evidence.
- Do not treat grep matches in changed files as blast-radius evidence.
- Do not certify results when required consumer or scan evidence is incomplete, including through cached results.
- Do not overwrite verified deep risk or sibling data with stale triage data; clear deep fields only when triage refresh invalidates that stage.
- Do not render a risk from a masked, absent, stale, or legacy stage.
- Do not render or follow up an unfixed or unverified instance as class-open.
- Do not create a follow-up issue directly. Only generate the body consumed by the existing approval gate.

## Testing strategy

- Run `pytest python/tests/issue/test_analyze_bugs.py`.
- Run changed-file pre-commit checks for the Python, test, agent, and skill files.
- Run `python3 python/cli.py lint agent-tool-contract`.
- Confirm existing analytics, sampling, evidence-token, cache, and report tests still pass.

difficulty: HARD
diff_lines: 620
