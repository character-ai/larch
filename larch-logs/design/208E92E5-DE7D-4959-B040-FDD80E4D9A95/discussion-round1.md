## Decision 1: Scope — all 5 OOS items in one PR
- **Question**: Should the design cover all 5 items in #2897 (A: step-7a SKIP_REASON; B: test-step-7a stale ledger; C: REASON_TOKEN parser embedded-`=`; D: ci-failed-jobs job_name leak; E: shared sanitize_diagnostic_line helper) or a subset?
- **Resolution**: All 5 items, single PR. Items share the diagnostic-sanitization + SKIP_REASON contract code area; the issue text explicitly permits "one PR or split as convenient".
- **Source**: user

## Decision 2: Helper reuse — Items C and D source Item E's helper
- **Question**: Should the sanitization in Items C and D route through Item E's new `sanitize_diagnostic_line` in `lib-quiet.sh`, or implement independently?
- **Resolution**: Yes. Item E lands first conceptually (extract helper into `lib-quiet.sh`), then Items C and D source it. Eliminates duplicated `tr -d [:cntrl:]` policy.
- **Source**: user

## Decision 3: Item C scope — harden parser only, do not expand contract
- **Question**: Should the SKIP_REASON contract be extended to support embedded `=` tokens, or only the parser hardened to tolerate them if they appear?
- **Resolution**: Harden parser only. Fix the `awk -F'[ =]'` parser at sanitize-mermaid-fragment.sh:283 so it preserves any future embedded `=` without expanding the token grammar today. No audit of other SKIP_REASON consumers required.
- **Source**: user

## Decision 4: Item D site — sanitize `$job_name` at parse boundary
- **Question**: Apply sanitization at every TSV/KV emit site, or once at the boundary where `$raw_name` is read from `gh` stdout?
- **Resolution**: Sanitize once at the parse boundary (around `ci-failed-jobs.sh:106-110`, immediately after `read -r raw_name`). Single chokepoint covers all downstream TSV/KV emits and any future ones.
- **Source**: user

## Decision 5: larch_err audit scope — only `ci-failed-jobs.sh`
- **Question**: Should the audit migrate every `larch_err` call site to the new helper, or only sites that demonstrably forward external content today?
- **Resolution**: Only `ci-failed-jobs.sh`. Codebase grep shows it is the sole `larch_err` site forwarding external (`gh`) stderr `$line`; every other `larch_err` argument is a fixed string or controlled local variable. Move the existing local `sanitize_diagnostic_line` from `ci-failed-jobs.sh` into `lib-quiet.sh`; `ci-failed-jobs.sh` sources it. New sites going forward should use the shared helper.
- **Source**: user + codebase

## Decision 6: Item B reconciliation direction — md adapts to harness identifiers
- **Question**: Reconcile by updating `test-step-7a.md` to match harness `new_case <label>` identifiers, or rename harness labels to match the md's descriptive names?
- **Resolution**: Update md to match harness identifiers. The harness `new_case` labels are the source of truth (used in case directory names and failure messages). Md becomes a 23-case ledger with kebab-case labels (`upsert-failure`, `argv-error`, etc.). Add the 2 missing cases (`rebase-unexpected-rc`, `quiet-diagram-skip-contract`). Fix the `diagram-failure-sanitizer` wording so it no longer claims the upsert is suppressed.
- **Source**: user + codebase

## Decision 7: Item A behavior — SKIP_REASON replaces placeholder when available; fallback when empty
- **Question**: Always replace the literal placeholder with `SKIP_REASON`, replace only when non-empty (fallback otherwise), or keep placeholder text and emit `SKIP_REASON` separately?
- **Resolution**: Replace when `SKIP_REASON` is non-empty; fall back to `"Code flow diagram not available."` when empty (e.g. generator emitted `STATUS=skipped` with no reason). Item B reconciliation includes updating harness assertions that currently check the literal placeholder so they assert the actual `SKIP_REASON` value when the test fixture sets one.
- **Source**: user
