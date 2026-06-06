## Decision 1: Fix breadth (producer-only vs producer + reader backstop)
- **Question**: Normalize at the producer only, or also harden the reader counters as defense-in-depth?
- **Resolution**: BOTH. Normalize at the producer (tally-code-votes.sh) AND harden both readers (oos-non-security-block-count.awk + python/oos.py) to also count the legacy `### FINDING_N: [OUT_OF_SCOPE]` header. Matches acceptance bullet 2; defends against any future producer emitting a legacy header.
- **Source**: user

## Decision 2: Drift coverage (which headers to normalize)
- **Question**: Normalize only `[OUT_OF_SCOPE]`-tagged blocks, or every non-`OOS_` header entering the accepted-OOS output?
- **Resolution**: ANY non-`OOS_` header. Rewrite to `### OOS_<k>:` for every block routed into the accepted-OOS output whose header is not already `### OOS_` — covers both the `[OUT_OF_SCOPE]` first-line tag AND the scope-fit gate's OUT_OF_SCOPE_DRIFT reclassification (which keeps a `### FINDING_N:` header with no tag and is silently dropped today).
- **Source**: user

## Decision 3: Cross-path scope (design-path OOS producer)
- **Question**: Does the design plan-review OOS producer need the same normalization?
- **Resolution**: NO. tally-plan-review.sh decides OOS-kind solely by id prefix (`case "$id" in OOS_*) kind="oos"`), with no `[OUT_OF_SCOPE]`-tag or scope-drift path, so it can only ever write `### OOS_` headers to oos-accepted-design.md. The design path is already canonical. Out of scope for this fix.
- **Source**: codebase

## Decision 4: Main-agent vote path
- **Question**: Does the code-review main-agent fallback vote need a separate producer fix?
- **Resolution**: NO. The main-agent vote path reuses tally-code-votes.sh as the producer, so the single producer fix covers it. (`oos-accepted-main-agent.md` is an artifact name, not a separate producer.)
- **Source**: codebase

## Decision 5: End-to-end filing requirement (does header normalization achieve filing?)
- **Question**: Is producer header normalization sufficient for the accepted OOS to actually be FILED (acceptance bullet 1), given the block body is review-finding-shaped, not OOS-item-shaped?
- **Resolution**: YES. The /implement Step 9a.1 batch builder (oos-pipeline.md step 3.3) also keys on `### OOS_N:` blocks, and the combine pass (step 3.4) is LLM-driven and reshapes the body into Description/Reviewer/Vote tally/Phase regardless of the input body schema. So normalizing only the header makes the counter count, the gate fire, the batch builder pick it up, and parse-input.sh (`^### OOS_[0-9]+:`) parse it. No body-schema change required in the producer.
- **Source**: codebase

## Decision 6: Both ship-driver gates in scope
- **Question**: Fix only one gate, or both?
- **Resolution**: BOTH. The bash gate (oos-non-security-block-count.awk via oos-disposition-gate.sh / ship-pr.sh) and the Python gate (python/oos.py via python/ship.py) must both be hardened, with regression tests in both harnesses (skills/implement/scripts/test-oos-disposition-gate.sh + python/test_oos.py / test_ship.py). Acceptance bullet 3.
- **Source**: issue + codebase

## Decision 7: Hard constraints (must not break)
- **Question**: What existing behavior must be preserved?
- **Resolution**: (a) Preserve the block body verbatim — only the `### <id>:` header line is rewritten, the title text after the id is preserved. (b) Keep the awk counter and its python port byte-for-byte semantically in parity (oos.py docstring: "Port oos-non-security-block-count.awk block counting"). (c) Avoid OOS id collisions in the accepted-OOS output (fresh sequential index strategy). (d) Security routing unchanged — security-focus OOS are held locally and never written to the accepted-OOS file, so the normalization (in the non-security write branch) cannot leak them. (e) Maintain parse-input.sh `^### OOS_[0-9]+:` grammar compatibility (numeric id, colon, space, title).
- **Source**: codebase
