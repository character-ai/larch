### External Reviewer Issues

- **Step review Step 2 — cursor-review failed (exit 1 — unknown — auth-retries=1, transient-retries=1)**:
  ```
===== diag =====
Error: [unavailable]
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)

===== additional failure diagnostics =====
===== diag =====
Error: [unavailable]
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-2/cursor-plan-innovation-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-2/cursor-plan-innovation-output.txt)

Reviewing the plan against the codebase and cited integration points.
Findings target plan overreach beyond the combined issue’s minimum fixes.

---

**1.** `[architecture]` `[SCOPE-REDUCTION]` **`python/agents.py:4866-4879`** — Implement stderr-tail “regeneration when a less-specific generic carrier masked launcher stderr” adds heuristic logic beyond Item 7. **`run_external_agent` already writes a tail on failure**; **`_append_implement_launch_failure` only needs compose + `resolve_failure_diagnostic_source(..., sink=str(sidecar))` for append-failure source selection.** **Revise:** drop carrier-specific regeneration; keep “write tail only when absent” after resolver selection.

**2.** `[architecture]` `[SCOPE-REDUCTION]` **`python/agents.py:4268-4280`** — Wiring compose/resolver/`stderr_sink` through all six `_review_emit_launcher_result` call sites (including **~4431** and **~4633** exit-0 paths) adds work on every successful review launch. **`classify_launch_failure` returns immediately on exit 0**; retry/NS-retry artifacts are absent on success. **Revise:** gate compose/resolver/sink forwarding to **`launcher_exit != 0`** and to preflight/emit-only paths (**~4352**, **~4361**, **~4561**, **~4577**) that skip `_review_append_launch_failure`.

**3.** `[correctness]` **`python/agents.py:4016-4028` vs `python/agents.py:4043-4055`** — Item 7 parity gap is real on emit-only paths: **`_review_append_launch_failure` already composes and passes `stderr_sink`**, but **`_review_emit_launcher_result` calls `_review_failure_source(output)` with no sink/compose**, so brainstorm/preflight failures that write **`args.stderr_sink`** can emit wrong **`LAUNCHER_FAILURE_*` KVs**. **Revise:** delegate `_review_failure_source` to the resolver (as planned) and pass **`stderr_sink` only on emit-only/non-zero paths**; avoid duplicating full compose on paths that already call `_review_append_launch_failure`.

**4.** `[OUT_OF_SCOPE]` **`python/collect_results.py:788-810`** — Per-candidate retry/NS-retry ordering before `.launch-stderr` is the right Item 6 fix; no change needed. Noted for downstream issue filing only if phase ordering tests slip.

---

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	architecture	python/agents.py:4866-4879	[SCOPE-REDUCTION] Implement stderr-tail regeneration heuristic exceeds Item 7 minimum run_external_agent already writes stderr-tail on failure; append-failure only needs compose plus resolver for source selection Regeneration rules for generic carriers add branching and tests without a required failure mode on the implement launch path	Drop less-specific-carrier regeneration; compose with sidecar sink resolve source for append-failure keep write-tail-if-absent only
1	in_scope	important	architecture	python/agents.py:4268-4280	[SCOPE-REDUCTION] Plan composes/resolves on all six _review_emit_launcher_result sites including exit-0 success calls at ~4431 and ~4633 Success paths pay compose/resolver I/O even though classify_launch_failure exits immediately on launcher_exit=0 and retry/NS-retry artifacts do not exist	Gate compose/resolver/sink forwarding to launcher_exit!=0 and emit-only preflight paths; leave success emit as lightweight KV emission
1	in_scope	important	correctness	python/agents.py:4016-4028	_review_emit_launcher_result omits stderr_sink compose while _review_append_launch_failure already uses sink Brainstorm/preflight paths write args.stderr_sink then emit without compose/resolver so LAUNCHER_FAILURE_* KVs can classify from bare .diag instead of sink/retry carriers	Delegate _review_failure_source to resolve_failure_diagnostic_source; pass stderr_sink on emit-only/non-zero paths; skip duplicate compose where append already ran
## Reviewer stderr (<TMPDIR>/plan-review/round-2/cursor-plan-innovation-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-2/cursor-plan-innovation-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-2/cursor-plan-innovation-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-2/cursor-plan-innovation-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-2/cursor-plan-innovation-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
✓ cursor agent: completed (exit code 0, output 4155 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-3/cursor-plan-innovation-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-3/cursor-plan-innovation-output.txt)

Reviewing the plan against the codebase to validate proposed changes and integration points.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	python/agents.py:4268-4280	[SCOPE-REDUCTION] `_review_emit_launcher_result` must not unconditionally call `_compose_failure_diag`	The plan wires every emit call (including `launcher_exit=0` at ~4431 and ~4633, and failure paths that already ran `_review_append_launch_failure` at ~4406/~4617) through compose-first source selection. Success emits can materialize `.failure-diag` from benign sidecar/events content; failure emits can append duplicate "additional failure diagnostics" sections after append already composed. Gate compose to preflight-only emit paths, or skip compose when append already ran / when `launcher_exit==0`. Forward `stderr_sink` and delegate `_review_failure_source` to `resolve_failure_diagnostic_source(output, sink=stderr_sink)` only.
2	in_scope	important	risk-integration	plan.txt:151-175; python/test_design_lifecycle.py; python/test_design_cli_ports.py	[SCOPE-REDUCTION] Item 9 Step 2b drafter argv/registry tests are outside the combined external-tool probe/diagnostic scope	The bundle targets probe retries, keychain locking, bounded diagnostic reads, collector stderr-tail parity, implement/review resolver alignment, and plan-review redaction. Design-drafter CLI argv smoke tests add ~two files and subprocess monkeypatching with no dependency on those runtime paths; the feature ships without them. Drop Item 9 from this change set and track it separately (or defer until a design-lifecycle-only task).
3	in_scope	important	correctness	python/agents.py:4017-4028; python/agents.py:4866-4879	Implement/review parity fixes differ in required surface area; implement compose+regeneration is necessary but emit compose is not	Item 7 requires implement-side `_compose_failure_diag(..., sink=str(sidecar))` plus conditional stderr-tail regeneration because `_append_implement_launch_failure` today prefers a generic `.diag` over the sidecar sink (~4869). Review parity for emit paths is satisfied by resolver delegation with `stderr_sink`; `_review_append_launch_failure` already composes before classification (~4054-4055). Keep the implement compose/regeneration steps; limit review emit changes to `stderr_sink` forwarding at the six call sites and `_review_failure_source` → `resolve_failure_diagnostic_source`, without mirroring implement-style regeneration in emit.

**Finding 1 — review emit compose**

`_review_emit_launcher_result` runs on every launch exit, including success. `_review_append_launch_failure` already composes on the main failure path. Unconditional compose in emit is extra surface and can duplicate or pollute `.failure-diag`.

**Finding 2 — Item 9**

Design-drafter tests belong in a design-lifecycle task, not this external-tool diagnostics bundle.

**Finding 3 — asymmetric parity**

Implement needs compose/regeneration; review emit does not need the same depth if resolver delegation plus existing append compose is used.
## Reviewer stderr (<TMPDIR>/plan-review/round-3/cursor-plan-innovation-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-3/cursor-plan-innovation-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-3/cursor-plan-innovation-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-3/cursor-plan-innovation-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-3/cursor-plan-innovation-output.txt.launch-stderr)

❌ cursor agent: FAILED (exit code 1, output 0 bytes)
⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 3466 bytes)
  ```
