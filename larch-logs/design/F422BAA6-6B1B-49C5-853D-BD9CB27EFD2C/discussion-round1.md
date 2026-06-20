## Decision 1: Item 2 — self-review tally dedup approach
- **Question**: How to dedupe the duplicated self-review tally logic (`audit_runs.py::_self_review_tally_rows` vs `fluff-analysis.py::_self_review_tally_records`) given `fluff-analysis.py` is deliberately stdlib-only and standalone (`python3 fluff-analysis.py`) while `audit_runs.py` lives in `python/`?
- **Resolution**: Extract a shared helper into `python/`. Import it from both callers. `fluff-analysis.py` gains a guarded `sys.path` bootstrap to import from `python/`. Accept the coupling cost (the standalone stdlib-only contract is relaxed to import one shared larch helper). The helper owns the drift-prone magic values: `mode == "self-review"`, the `accepted_count` / `rejected_count` keys, and the `SELF_REVIEW_ACCEPTED` / `SELF_REVIEW_REJECTED` prefixes. Each caller keeps its own record-shape construction (no behavior change to either output).
- **Source**: user

## Decision 2: Item 3 — secret-scrub fail-closed vs warn asymmetry
- **Question**: How to handle the claimed fail-closed vs warn-only secret-scrub asymmetry (source #4854 had an empty body), given the audit shows most paths already fail closed?
- **Resolution**: Force fail-closed everywhere. Every scrub/redact path must abort (not warn-and-proceed) when the scrubber errors or a detected secret survives scrubbing. Lock the invariant with regression tests across each path. Convert any genuine warn-on-scrub-error path to abort. Hard constraint: success-case rotation warnings (a secret was found AND successfully scrubbed) stay warnings — you cannot "fail closed" after the secret is already removed; those are not the target.
- **Source**: user

## Decision 3: Item 1 — implement vs design sentinel-probe wording
- **Question**: How to reconcile `/implement` NEVER-list recovery wording against the `/design`-only foreground-probe carve-out, given the current implement SKILL.md NEVER #8 already explains the asymmetry and a test harness pins it?
- **Resolution**: Add a minimal cross-reference note to the implement-side wording making the intentional, non-contradictory asymmetry explicit (implement is notification-only because it writes no `*-terminal` sentinels; the `/design` foreground probe is a deliberate carve-out, not a contradiction). No behavior change. Pin the new clause in `scripts/test-implement-anti-polling-rule.sh` so it cannot silently drift.
- **Source**: user

## Scope boundaries (binding)
- In scope: the 3 items above, minimal-change each.
- Out of scope: refactoring unrelated scrub/redact logic; changing the `code-review-tally.json` schema; altering success-case rotation warnings; rewriting the full NEVER lists.
- Must not break: existing `fluff-analysis.py` record output, `audit_runs.py` row output, the anti-polling test harness, and all existing scrub fail-closed behavior.
- Security-relevant (Item 3) → `SECURITY.md` update required per AGENTS.md.
