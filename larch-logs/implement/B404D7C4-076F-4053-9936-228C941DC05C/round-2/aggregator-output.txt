### FINDING_1: [OUT_OF_SCOPE] Bootstrap wrapper self-derivation can resolve the wrong tree or fail unclearly
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `implement-bootstrap-invoke.sh` derives `CLAUDE_PLUGIN_ROOT` from `$0` for non-contract invocations but does not validate plugin layout at the derive site. Relative, symlinked, copied, or failed-`cd` cases can produce a wrong or empty root and fail later with unclear errors; current tests cover only successful self-derive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Add post-derive existence check for implement-bootstrap.sh or fail at derive site with clear message.
  - From cursor-specialist-testing-output.txt: Add negative sandbox case where derivation yields empty value and assert non-zero exit with CLAUDE_PLUGIN_ROOT must be set

### FINDING_2: [OUT_OF_SCOPE] `append-execution-issue.sh --log` accepts arbitrary caller-supplied paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Pre-existing behavior allows `--log` to target any writable path without root-prefix or canonicalization checks. The reviewed diff does not widen this surface, but mis-invoking callers can write execution-issue logs outside the intended location.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_3: Step 5 dynamic-archetypes banner cap can diverge from the cap actually used
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-step5-runtime-output.txt
- **Severity**: important
- **Concern**: The Step 5 fence resolves `dynamic_archetypes_cap` using ambient process env before session-env, while `run-step5-review.sh` forwards session-env as a CLI value that `review-and-fix.sh` treats as higher precedence. The same fence also references an inert `dynamic_archetypes_value` tier that later Bash subprocesses do not receive. This can make the banner report one cap while review runs another, or fail preflight on an ambient value even when session-env contains a valid cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reorder fence to read session-env first (mirror run-step5-review CLI source), then process env, then default 6.
  - From cursor-specialist-edge-cases-output.txt: Remove dead tier or wire Step 0 export/routing key; align prose with review-and-fix.sh precedence.
  - From dyn-step5-runtime-output.txt: Reorder the fence to read `LARCH_DYNAMIC_ARCHETYPES_MAX` from session-env first (matching `run-step5-review.sh`), fall back to non-empty process env only when session-env is empty, then default to `6`; validate after resolution; add a harness case with conflicting session-env vs ambient values asserting banner matches forwarded CLI.
  - From dyn-step5-runtime-output.txt: Drop the dead `${dynamic_archetypes_value:-}` branch from the fence and align prose with the actual source order (session-env → ambient → default), or export a durable key into session-env only and read that single source in both the fence and `run-step5-review.sh`.

### FINDING_4: [OUT_OF_SCOPE] Step 5 preflight-failure routing and Warnings logging are underspecified
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-step5-runtime-output.txt, dyn-make-harness-output.txt
- **Severity**: important
- **Concern**: Step 5 prose says to treat non-zero fence exit or non-integer telemetry as hard preflight failure and log to `Warnings`, but does not clearly say whether to stall, continue with defaults, skip `run-step5-review.sh`, or route to Step 18. It also lacks a literal `append-execution-issue.sh --log ... --category Warnings --entry ...` example, leaving the prior helper-argv misuse mode live on this new path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Define explicit failure routing: stall or use documented safe defaults; never continue with unset banner variables.
  - From dyn-step5-runtime-output.txt: State explicitly that a failed telemetry fence must not invoke `run-step5-review.sh` (or must set `STALL_TRACKING` and route to Step 18), and add one fenced example: `append-execution-issue.sh --log "$IMPLEMENT_TMPDIR/execution-issues.md" --category Warnings --entry "- **Step 5**: banner preflight failed: …"`.
  - From dyn-step5-runtime-output.txt: Address the concern above.
  - From dyn-make-harness-output.txt: Add a literal one-line `append-execution-issue.sh` invocation at `skills/implement/SKILL.md:812` (and mirror it at the Step 2 call site around line 630), using the `USAGE=` contract from `scripts/append-execution-issue.sh`.

### FINDING_5: Bootstrap self-derive test hides stderr diagnostics
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The new derive test discards stderr, so failures surface only as return-code or stdout mismatches without the wrapper’s actual error context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Capture stderr to artifact file and print on failure.

### FINDING_6: Step 5 telemetry fence adds an unpinned prompt-side KV contract and duplicated cap logic
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-make-harness-output.txt, dyn-quiet-contract-output.txt
- **Severity**: important
- **Concern**: The Step 5 telemetry fence now computes banner values, calls `lib-implement-round-cap.sh`, and emits ad-hoc stdout KVs that prompt-side orchestration must parse. This duplicates runtime precedence logic, expands beyond the plan’s intended prose-only degraded-round directive, and lacks CI structure tests pinning the CLI call and emitted KV names.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Revert to prose-only CLI directive per plan or add structure harness pinning fence CLI invocation and KV printf lines
  - From cursor-specialist-testing-output.txt: Extend test-implement-structure.sh Step 5 region to require --count-prior-degraded and emitted KV line patterns
  - From dyn-make-harness-output.txt: Either revert to the plan’s prose-only CLI directive (`lib-implement-round-cap.sh --count-prior-degraded …` in orchestrator prose, no expanded fence), or add a `scripts/test-implement-structure.sh` assertion that the Step 5 region contains `--count-prior-degraded` and the four `printf` KV lines.
  - From dyn-quiet-contract-output.txt: Revert the fence to telemetry-only (as in `1bd5a94a1`); keep the degraded-round fix as a single CLI invocation in prose or one assignment line, without moving the full `dynamic_archetypes_cap` derivation into the fence.

### FINDING_7: `append-execution-issue.sh` fail-usage tests miss remaining branches
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The harness checks only some `fail_usage` paths, so unsupported-category or mutual-exclusive-entry regressions could drop `USAGE=` without failing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add table-driven cases for remaining exit-1 fail_usage paths

### FINDING_8: [OUT_OF_SCOPE] Harness shard docs were not updated
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` does not document the new `test-append-execution-issue` shard placement, despite an edit-in-sync note. CI still passes via Makefile coverage, but contributor discovery may suffer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update docs/linting.md harness section when adding Makefile-only harnesses (optional follow-up)

### FINDING_9: Happy-path append test does not prove entries land under `Warnings`
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The append-execution happy-path test only checks that the file contains both the `Warnings` header and the entry somewhere. A regression inserting the warning under another section would still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Extract the Warnings section or add a following header and assert the entry appears before the next section.

### FINDING_10: Round-cap inert-source test does not cover CLI-shaped positional args
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The inert-source test does not source `lib-implement-round-cap.sh` with `--count-prior-degraded`-shaped arguments, so a guard bug that exits only for CLI-shaped args while sourced would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Add a source test using --count-prior-degraded-shaped args and assert no usage/exit occurs and the function remains callable.

### FINDING_11: [OUT_OF_SCOPE] `run-step5-review.md` launcher docs are stale
- **Reviewer(s)**: dyn-step5-runtime-output.txt
- **Severity**: latent
- **Concern**: The docs still describe a `--round-num`-required, `--mode diff`-only launcher and omit `--mode loop` plus session-env dynamic-archetypes forwarding, widening drift now that Step 5 banner logic depends on that launcher contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step5-runtime-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] `append-execution-issue.sh` blurs usage-vs-I/O failure classes for unreadable entry files
- **Reviewer(s)**: dyn-quiet-contract-output.txt
- **Severity**: latent
- **Concern**: An unreadable `--entry-file` is currently routed through `fail_usage`, producing exit 1 and `USAGE=` even though the argv shape is valid and the failure is a runtime readability problem. Tests also do not pin that exit-2 I/O envelopes omit `USAGE=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-contract-output.txt: Handle unreadable `--entry-file` with the exit-`2` I/O envelope (no `USAGE=`), or document and test it as an explicit third validation class if `USAGE=` on path errors is intentional.
  - From dyn-quiet-contract-output.txt: Address the concern above.

### FINDING_13: Helper CLI failure-output conventions diverge from the shared quiet contract
- **Reviewer(s)**: dyn-quiet-contract-output.txt
- **Severity**: latent
- **Concern**: The branch introduces or exposes inconsistent CLI contracts: `append-execution-issue.sh` adds a `USAGE=` quiet-envelope key, while `lib-implement-round-cap.sh` emits raw stderr usage and bare stdout integers. The shared `lib-quiet.md` authority does not document optional failure envelope keys, leaving callers without one reusable parsing model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-contract-output.txt: Document in `scripts/lib-quiet.md` when optional `USAGE=` is permitted on quiet helpers, and either align round-cap CLI errors with `emit_kv` or explicitly classify it as a “numeric probe” exception with a shared naming table for failure keys.
  - From dyn-quiet-contract-output.txt: Add a short “optional failure envelope keys” subsection to `lib-quiet.md` (`FAILED`, `ERROR`, optional `USAGE`) and cross-link from `append-execution-issue.md`.

### FINDING_14: [OUT_OF_SCOPE] Step 2 still lacks a literal `append-execution-issue.sh` example
- **Reviewer(s)**: dyn-quiet-contract-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/SKILL.md` references `append-execution-issue.sh` near the Step 2 branch-mismatch path without a copy-pasteable `--log` / `--category` / `--entry` example. The new `USAGE=` synopsis helps runtime discovery but does not close this pre-existing DX gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-contract-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Sibling helper lacks `USAGE=` parity
- **Reviewer(s)**: dyn-quiet-contract-output.txt
- **Severity**: latent
- **Concern**: Pre-existing `append-tool-failure.sh` emits only `FAILED`/`ERROR` on usage failure and does not match the new `USAGE=` pattern, amplifying helper-contract inconsistency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-contract-output.txt: Address the concern above.
