## Goal
Implement issue #7212: [IMPLEMENTING] bug-treadmill [FEATURE] 6971.2: introduced_risk and class-completeness verdicts: agent schema, ledger ingest, and report sections.

## Implementation Plan
Partition piece 2 of 2 split from #6971 (operator-directed split of an approved [DESIGNED] plan; each piece carries its carved plan section verbatim, so [DESIGNED] status is retained).

**Scope**: Extend the agent contracts (`.claude/agents/bug-fix-triage.md`: required `introduced_risk` plus evidence reason; `.claude/agents/bug-fix-verifier.md`: `introduced_risk`, `class_complete`, `sibling_sites` with mandatory targeted Greps), the strict-key ledger ingest with `legacy_schema` marking for prior-shape rows, provenance-preserving serialization with refresh clearing, and the report: an `Introduced risk` section and an `Instance fixed, class open` section whose rows join the approval-gated follow-up body. Consumes the scan-status and consumer evidence from the sibling evidence piece.

**Firm headings**: .claude/agents/bug-fix-triage.md, .claude/agents/bug-fix-verifier.md, python/larch/issue/analyze_bugs.py, .claude/skills/analyze-bugs/SKILL.md, python/tests/issue/test_analyze_bugs.py

**Acceptance**:

A fixture reproducing the #6632 shape (same regex duplicated in two modules, one fixed) yields `class_complete=false` with the sibling site listed; both new report sections render; class-open items reach the follow-up body file; legacy rows ingest as `legacy_schema=true` without forcing `--refresh`; `python3 python/cli.py lint agent-tool-contract` passes.

**Dependencies (from split)**: blocked-by Piece 1

```
<!-- larch:plan:start -->
## Plan

## Approach

Evolve agent and ledger schemas additively, retain stage-specific evidence, and distinguish an instance verdict from class completeness. Render verified introduced risks and only confirmed-instance class-open findings without changing approval-gated filing. The evidence layer this consumes (consumer sections, scan-status stanzas, widened scans) landed in the sibling piece.

## Files to modify/create

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

### UPDATED: python/larch/issue/analyze_bugs.py

- Add stage-specific `introduced_risk` and evidence-reason fields, plus `class_complete`, `sibling_sites`, and `legacy_schema`, to ingest and ledger records.
- Accept exactly the prior or current triage and verifier key sets. Mark prior shapes as `legacy_schema=true`; reject partial, mixed, or extra-key shapes.
- Validate current triage and verifier `introduced_risk` values as non-empty strings: `none found` is the exact no-risk sentinel; any other value is a risk claim and requires a non-empty introduced-risk evidence reason. Reject malformed or incoherent current rows instead of defaulting them.
- For current verifier rows, validate `class_complete` as a boolean and `sibling_sites` as valid `path:symbol` strings. For `CONFIRMED_FIXED`, require non-empty sibling sites when `class_complete=false`; require an empty sibling list when `class_complete=true`. For non-confirmed instance verdicts, permit `class_complete=false` with an empty list so fail-closed verifier results remain ingestible.
- Detect persisted records missing current fields during ledger loading and mark them legacy rather than defaulting them into current claims.
- Preserve new fields and their originating stage through ledger serialization and loading. On refreshed triage, clear all invalidated deep-stage risk, class-completeness, sibling-site, and evidence fields rather than retaining stale deep data.
- Render `## Introduced risk` only for non-legacy rows with a present selected-stage risk other than `none found`: prefer completed deep-stage risk and its evidence reason, otherwise use valid triage-stage risk and its evidence reason.
- Render `## Instance fixed, class open` only for non-legacy rows with completed current-schema verifier output, an instance verdict of `CONFIRMED_FIXED`, `class_complete=false`, and non-empty validated sibling sites.
- Build the follow-up body from terminal-verdict follow-ups plus those eligible confirmed-instance class-open rows. Write `follow-up-issue.md` when either set is non-empty, while preserving the existing approval-gated filing path.

### UPDATED: .claude/skills/analyze-bugs/SKILL.md

- Describe stage-specific risk precedence, legacy-row suppression, instance-verdict/class-completeness separation, both report sections, and confirmed-instance-only class-open follow-up behavior.

### UPDATED: python/tests/issue/test_analyze_bugs.py

- Cover exact current schemas, accepted legacy schemas, legacy marking during ingest and persisted-ledger loading, and rejection of partial, mixed, extra-key, malformed, empty, or incoherent current rows.
- Add current-triage tests rejecting invalid `introduced_risk` values and missing risk evidence reasons while confirming prior triage rows ingest as legacy.
- Verify `CONFIRMED_FIXED` plus `class_complete=false` requires valid non-empty `path:symbol` sibling sites, `class_complete=true` requires an empty sibling list, and non-confirmed fail-closed verifier verdicts can use `class_complete=false` with an empty list.
- Extend the #6946-shaped fixture with a non-none verifier introduced-risk result and the targeted checkout-Grep contract text.
- Add the #6632-shaped end-to-end fixture: duplicate the same regex or pattern in two modules, fix only one module, ingest a `CONFIRMED_FIXED` verifier result with `class_complete=false` and the other module's sibling site, then assert class-open report and follow-up eligibility.
- Verify non-confirmed instance rows, including rows with sibling data, never render as `Instance fixed, class open` and never enter class-open follow-ups.
- Verify ledger round trips retain stage-specific risk provenance and triage refresh clears stale deep risk and class data.
- Add verifier-contract assertions for targeted risk Grep, class-completeness Grep, failed-scan handling, and the required new fields.
- Add report fixture coverage for triage-only and deep-stage risk precedence, legacy suppression, one introduced-risk row, one eligible class-open row, and class-open-only follow-up body generation.

## Edge cases

- Legacy rows remain usable but cannot render introduced-risk or class-completeness claims.
- `none found` risks stay out of alert sections and follow-up content.
- A non-confirmed instance verdict cannot be reported as fixed merely because its class is incomplete.

## Failure modes

- Reject malformed current-version agent rows rather than silently dropping or defaulting fields.
- Do not overwrite verified deep risk or sibling data with stale triage data; clear deep fields only when triage refresh invalidates that stage.
- Do not render a risk from a masked, absent, stale, or legacy stage.
- Do not render or follow up an unfixed or unverified instance as class-open.
- Do not create a follow-up issue directly. Only generate the body consumed by the existing approval gate.

## Testing strategy

- Run `pytest python/tests/issue/test_analyze_bugs.py`.
- Run changed-file pre-commit checks for the Python, test, agent, and skill files.
- Run `python3 python/cli.py lint agent-tool-contract`.
- Confirm existing analytics, sampling, evidence-token, cache, and report tests still pass.

## Acceptance

- Run `pytest python/tests/issue/test_analyze_bugs.py`.
- Run changed-file pre-commit checks for the Python, test, agent, and skill files.
- Run `python3 python/cli.py lint agent-tool-contract`.
- Confirm existing analytics, sampling, evidence-token, cache, and report tests still pass.
- Both new report sections render; class-open items reach the follow-up body file; agent docs and `.claude/skills/analyze-bugs/SKILL.md` updated.

review_status: complete
rounds_completed: 2
difficulty: HARD
diff_added: 285
diff_deleted: 5
mechanical_churn: false
diff_lines: 290
<!-- larch:plan:end -->
```

**Original feature context (excerpt)**:

Parent #6971. Class completeness: a fix that fully addresses the described instance gets `FIXED_CLEAR`, honestly, while sibling sites keep the class alive: #6610 to #6668, #6632 to #6672, #6882 to #6955. The funnel never asks whether the pattern survives elsewhere. #6672 states the mechanism: "Each fix landed one axis at a time because nothing mechanically prevents a second parser literal." This piece adds the verdict vocabulary (`introduced_risk`, `class_complete`, `sibling_sites`), additive strict-key ledger evolution with `legacy_schema` marking so `--refresh` is not forced, and the two report sections whose class-open rows feed the existing approval-gated `/issue` follow-up filing.

## Test plan
(no test plan section in plan-file)
