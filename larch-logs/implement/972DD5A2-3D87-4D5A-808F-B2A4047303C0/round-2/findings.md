### FINDING_1: **Important** (`correctness`) — `scripts/harness-timer.sh:8-14` — If **`python3` fails** (missing binary, spawn error, or bad `start`/`end` values breaking the `elapsed` one-liner), execution can stop **before** `printf`, so callers may see **no `LARCH_HARNESS_TIMING` line** and an exit status that **no longer mirrors** the inner command’s code. That breaks the documented mirror contract on the failure path of the timing machinery itself. Fail loud with a fixed diagnostic exit, or run timing in one Python process with explicit error handling, and document that Python failure aborts timing.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 3. **Important** (`correctness`) — `scripts/harness-timer.sh:8-14` — If **`python3` fails** (missing binary, spawn error, or bad `start`/`end` values breaking the `elapsed` one-liner), execution can stop **before** `printf`, so callers may see **no `LARCH_HARNESS_TIMING` line** and an exit status that **no longer mirrors** the inner command’s code. That breaks the documented mirror contract on the failure path of the timing machinery itself. Fail loud with a fixed diagnostic exit, or run timing in one Python process with explicit error handling, and document that Python failure aborts timing.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** (`correctness`) — `scripts/test-harness-timer.sh:35-41` — The `sleep 0.5` case caps at **`0.79s`**, but `harness-timer.sh` measures wall time from **after** the first `python3` snapshot through the second snapshot **after** the sleep, so the measured interval includes at least one extra `python3 -c` invocation on the hot path. On cold or overloaded hosts, `sleep 0.5` plus that overhead can exceed **`0.80s`** even when the wrapper is correct, producing **flake failures** on `test-harness-timer` / shard 12. Widen the upper bound, measure overhead separately, or anchor the assertion to the prompt’s regex plus a documented slop policy.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **Important** (`correctness`) — `scripts/test-harness-timer.sh:35-41` — The `sleep 0.5` case caps at **`0.79s`**, but `harness-timer.sh` measures wall time from **after** the first `python3` snapshot through the second snapshot **after** the sleep, so the measured interval includes at least one extra `python3 -c` invocation on the hot path. On cold or overloaded hosts, `sleep 0.5` plus that overhead can exceed **`0.80s`** even when the wrapper is correct, producing **flake failures** on `test-harness-timer` / shard 12. Widen the upper bound, measure overhead separately, or anchor the assertion to the prompt’s regex plus a documented slop policy.
- **Suggested revision**: Address the concern above.

### FINDING_3: **Important** (`risk-integration`) — `scripts/test-harness-timer.sh:35-50`, `scripts/test-harness-timer.md:1-10` — The regression harness checks **numeric bands** (`0.40`–`0.79`, `1.90`–`4.99`) plus a fixed `N.NNs` shape, not the **prompt’s** acceptance patterns (`^0\.[4-6][0-9]s$` for the half-second case, `^[12]\.[0-9]{2}s$` for the two-second case). A run that took ~`3.45s` after `sleep 2` would **fail** the stated regex but **pass** this harness, so CI can stay green while the contract described in the feature text is violated. Tighten assertions to those regexes (or update the feature/docs to explicitly allow the wider bands and explain why).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **Important** (`risk-integration`) — `scripts/test-harness-timer.sh:35-50`, `scripts/test-harness-timer.md:1-10` — The regression harness checks **numeric bands** (`0.40`–`0.79`, `1.90`–`4.99`) plus a fixed `N.NNs` shape, not the **prompt’s** acceptance patterns (`^0\.[4-6][0-9]s$` for the half-second case, `^[12]\.[0-9]{2}s$` for the two-second case). A run that took ~`3.45s` after `sleep 2` would **fail** the stated regex but **pass** this harness, so CI can stay green while the contract described in the feature text is violated. Tighten assertions to those regexes (or update the feature/docs to explicitly allow the wider bands and explain why).
- **Suggested revision**: Address the concern above.

### FINDING_4: **Latent** (`correctness`) — `scripts/harness-timer.sh:12`, `scripts/harness-timer.md:28-30` — If the wall clock moves backward (`end < start`), Python emits a **negative** fractional string, which **does not** match the published parser token `^[0-9]+(\.[0-9]+)?s$`, so a rare VM/NTP adjustment yields **log lines parsers reject** without any inner harness fault. Clamp elapsed at `0.00s`, or extend the contract to cover negatives and add a test if that is intentional.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 4. **Latent** (`correctness`) — `scripts/harness-timer.sh:12`, `scripts/harness-timer.md:28-30` — If the wall clock moves backward (`end < start`), Python emits a **negative** fractional string, which **does not** match the published parser token `^[0-9]+(\.[0-9]+)?s$`, so a rare VM/NTP adjustment yields **log lines parsers reject** without any inner harness fault. Clamp elapsed at `0.00s`, or extend the contract to cover negatives and add a test if that is intentional.
- **Suggested revision**: Address the concern above.

### FINDING_5: **Nit** (`code-quality`) — `scripts/test-harness-timer.sh:61-64` — The `false` case only checks that the timing field is **non-empty**, not that it matches the **`N.NNs`** shape or the public regex. A bogus third column would still pass. Reuse `timing_in_range` with a trivial non-negative window or assert the same regex used elsewhere in the file.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 5. **Nit** (`code-quality`) — `scripts/test-harness-timer.sh:61-64` — The `false` case only checks that the timing field is **non-empty**, not that it matches the **`N.NNs`** shape or the public regex. A bogus third column would still pass. Reuse `timing_in_range` with a trivial non-negative window or assert the same regex used elsewhere in the file.
- **Suggested revision**: Address the concern above.

### FINDING_6: **Nit** `code-quality` `scripts/test-harness-timer.sh:44` — The `sleep 2` regression accepts `1.90s-4.99s`, but the requested contract was `^[12]\.[0-9]{2}s$`. This would let a future timer regression reporting `3.xx` or `4.xx` for a 2-second command pass the test. Tighten the assertion to the requested regex or cap the range at `2.99s`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `code-quality` `scripts/test-harness-timer.sh:44` — The `sleep 2` regression accepts `1.90s-4.99s`, but the requested contract was `^[12]\.[0-9]{2}s$`. This would let a future timer regression reporting `3.xx` or `4.xx` for a 2-second command pass the test. Tighten the assertion to the requested regex or cap the range at `2.99s`.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] **Nit** (`architecture`) — `scripts/harness-timer.sh:7-9` — There is still **no arity guard** (`name="$1"; shift` then `"$@"`); calling the wrapper with fewer than two arguments yields empty or odd behavior. That pattern predates the fractional change and is not worsened by it; add validation only if you want stricter contracts generally.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **Nit** (`architecture`) — `scripts/harness-timer.sh:7-9` — There is still **no arity guard** (`name="$1"; shift` then `"$@"`); calling the wrapper with fewer than two arguments yields empty or odd behavior. That pattern predates the fractional change and is not worsened by it; add validation only if you want stricter contracts generally. ```tsv schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix 1	in_scope	important	risk_integration	scripts/test-harness-timer.sh:35-50;scripts/test-harness-timer.md:1-10	Tests enforce wide numeric bands (0.40-0.79 and 1.90-4.99) instead of the feature-stated regexes (^0.[4-6][0-9]s$ and ^[12].[0-9]{2}s$).	A ~3.45s wall time after sleep 2 passes the harness but violates the prompt regex, so CI can miss contract drift.	Align assertions with the prompt regexes or revise the written contract to match the chosen bands. 2	in_scope	important	correctness	scripts/test-harness-timer.sh:35-41	The sleep 0.5 assertion caps at 0.79s while harness-timer includes post-start python snapshot overhead in the measured interval.	Slow runners can exceed 0.80s total and fail intermittently despite correct timing logic.	Widen bounds, subtract measured overhead, or encode the prompt regex with explicit slop notes. 3	in_scope	important	correctness	scripts/harness-timer.sh:8-14	Python timing subprocess failures can abort before printf, breaking exit-code mirroring and timing emission.	A broken python3 on a shard yields missing LARCH lines and wrong outer exit codes versus the inner harness.	Add explicit error handling or single-process timing; document fatal behavior on python failure. 4	in_scope	latent	correctness	scripts/harness-timer.sh:12;scripts/harness-timer.md:28-30	Negative end-start yields a negative timing token that violates the documented ^[0-9]+(\.[0-9]+)?s$ contract.	Rare clock skew produces parser-invalid rows without inner test failure.	Clamp at 0.00s or extend the contract and tests for negatives. 5	in_scope	nit	code_quality	scripts/test-harness-timer.sh:61-64	The false case does not validate timing token shape, only non-emptiness.	Garbage in column three could still satisfy the check.	Assert the same regex or timing_in_range as other cases. 6	out_of_scope	nit	architecture	scripts/harness-timer.sh:7-9	No minimum-argument validation remains on harness-timer.sh.	Mis-invocation can run an empty command; behavior is pre-existing and unchanged in spirit.	Add explicit usage errors if tightening the wrapper contract is desired. ```
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/harness-timer.sh:12-13
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Elapsed python invocation failure can yield empty elapsed and malformed timing column. Rare python failure prints LARCH_HARNESS_TIMING with empty duration. Guard: validate python exit status or default/fail closed before printf.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/test-harness-timer.md:6-10
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Test harness stub documents only range checks, not the regex contract from the feature/plan. Readers comparing stub to issue text see different acceptance rules. Add the regexes or a verbatim quote of the plan’s assertion lines.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/test-harness-timer.sh:18-51 scripts/test-harness-timer.md:8-9
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Sleep timing assertions use inclusive numeric ranges instead of the plan/feature regexes ^0\.[4-6][0-9]s$ and ^[12]\.[0-9]{2}s$. A broken timer could emit values outside those regexes (e.g. 3.45s after sleep 2, or 0.75s after sleep 0.5) and still pass CI, while failing the documented acceptance criteria. Implement the regex checks from the plan or update the plan/feature to the chosen windows and align the sibling doc.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/test-harness-timer.sh:35-41
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Regression test uses 0.40-0.79s range instead of required ^0.[4-6][0-9]s$ from feature_description and plan. 0.75s passes tests but fails the ticket regex (tenths digit outside 4-6). Use the specified regex or a range logically equivalent to it (e.g. cap tenths at 6) if CI slop requires widening, and document deviation.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/test-harness-timer.sh:44-50
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Regression test uses numeric range 1.90-4.99 instead of required ^[12].[0-9]{2}s$ from feature_description and plan. A buggy timer emitting 3.50s for sleep 2 passes the harness but violates the specified regex contract. Replace range check with regex match (or tighten range to 1.00-2.99 and add major-second sanity) per spec.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/test-harness-timer.sh:53-64
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] false case only asserts non-empty timing token, not shape. Malformed non-empty third field could pass despite invalid duration format. Assert timing matches the same format/regex as other cases or the documented parser contract.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/harness-timer.sh:8-13
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] harness-timer runs three separate python3 processes per invocation. Sub-second resolution improves but wall-clock overhead shifts timing distributions vs date +%s. Optionally combine into one python3 -c for start/end/delta if rebalancing noise matters.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/test-harness-timer.sh:35-42
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] sleep 0.5 uses 0.40–0.79s band instead of the plan’s ^0\.[4-6][0-9]s$ pattern. Values such as 0.78s pass the test but fail the stated regex (tenths digit outside 4–6). Match the plan regex or document intentional relaxation in harness-timer.md / test-harness-timer.md.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/test-harness-timer.sh:44-51
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] sleep 2 assertion is only a wide numeric range (1.90–4.99) with no leading-whole-digit constraint from the plan. A buggy duration like 3.00s still passes while violating the specified ^[12]\.[0-9]{2}s$ acceptance. Add a regex (or equivalent) for ^[12]\.[0-9]{2}s$ and/or cap max near expected wall time (e.g. ~2.5s) instead of 4.99s.
- **Suggested revision**: Address the concern above.

