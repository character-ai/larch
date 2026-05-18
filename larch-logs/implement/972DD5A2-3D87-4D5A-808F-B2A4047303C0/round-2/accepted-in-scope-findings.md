### FINDING_13: correctness: scripts/test-harness-timer.sh:53-64
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] false case only asserts non-empty timing token, not shape. Malformed non-empty third field could pass despite invalid duration format. Assert timing matches the same format/regex as other cases or the documented parser contract.
- **Suggested revision**: Address the concern above.


### FINDING_2: **Important** (`correctness`) — `scripts/test-harness-timer.sh:35-41` — The `sleep 0.5` case caps at **`0.79s`**, but `harness-timer.sh` measures wall time from **after** the first `python3` snapshot through the second snapshot **after** the sleep, so the measured interval includes at least one extra `python3 -c` invocation on the hot path. On cold or overloaded hosts, `sleep 0.5` plus that overhead can exceed **`0.80s`** even when the wrapper is correct, producing **flake failures** on `test-harness-timer` / shard 12. Widen the upper bound, measure overhead separately, or anchor the assertion to the prompt’s regex plus a documented slop policy.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **Important** (`correctness`) — `scripts/test-harness-timer.sh:35-41` — The `sleep 0.5` case caps at **`0.79s`**, but `harness-timer.sh` measures wall time from **after** the first `python3` snapshot through the second snapshot **after** the sleep, so the measured interval includes at least one extra `python3 -c` invocation on the hot path. On cold or overloaded hosts, `sleep 0.5` plus that overhead can exceed **`0.80s`** even when the wrapper is correct, producing **flake failures** on `test-harness-timer` / shard 12. Widen the upper bound, measure overhead separately, or anchor the assertion to the prompt’s regex plus a documented slop policy.
- **Suggested revision**: Address the concern above.


### FINDING_4: **Latent** (`correctness`) — `scripts/harness-timer.sh:12`, `scripts/harness-timer.md:28-30` — If the wall clock moves backward (`end < start`), Python emits a **negative** fractional string, which **does not** match the published parser token `^[0-9]+(\.[0-9]+)?s$`, so a rare VM/NTP adjustment yields **log lines parsers reject** without any inner harness fault. Clamp elapsed at `0.00s`, or extend the contract to cover negatives and add a test if that is intentional.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 4. **Latent** (`correctness`) — `scripts/harness-timer.sh:12`, `scripts/harness-timer.md:28-30` — If the wall clock moves backward (`end < start`), Python emits a **negative** fractional string, which **does not** match the published parser token `^[0-9]+(\.[0-9]+)?s$`, so a rare VM/NTP adjustment yields **log lines parsers reject** without any inner harness fault. Clamp elapsed at `0.00s`, or extend the contract to cover negatives and add a test if that is intentional.
- **Suggested revision**: Address the concern above.


### FINDING_5: **Nit** (`code-quality`) — `scripts/test-harness-timer.sh:61-64` — The `false` case only checks that the timing field is **non-empty**, not that it matches the **`N.NNs`** shape or the public regex. A bogus third column would still pass. Reuse `timing_in_range` with a trivial non-negative window or assert the same regex used elsewhere in the file.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 5. **Nit** (`code-quality`) — `scripts/test-harness-timer.sh:61-64` — The `false` case only checks that the timing field is **non-empty**, not that it matches the **`N.NNs`** shape or the public regex. A bogus third column would still pass. Reuse `timing_in_range` with a trivial non-negative window or assert the same regex used elsewhere in the file.
- **Suggested revision**: Address the concern above.


