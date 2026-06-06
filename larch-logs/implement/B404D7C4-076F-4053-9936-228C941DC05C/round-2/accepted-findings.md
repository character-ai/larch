### FINDING_3: Step 5 dynamic-archetypes banner cap can diverge from the cap actually used
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-step5-runtime-output.txt
- **Severity**: important
- **Concern**: The Step 5 fence resolves `dynamic_archetypes_cap` using ambient process env before session-env, while `run-step5-review.sh` forwards session-env as a CLI value that `review-and-fix.sh` treats as higher precedence. The same fence also references an inert `dynamic_archetypes_value` tier that later Bash subprocesses do not receive. This can make the banner report one cap while review runs another, or fail preflight on an ambient value even when session-env contains a valid cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reorder fence to read session-env first (mirror run-step5-review CLI source), then process env, then default 6.
  - From cursor-specialist-edge-cases-output.txt: Remove dead tier or wire Step 0 export/routing key; align prose with review-and-fix.sh precedence.
  - From dyn-step5-runtime-output.txt: Reorder the fence to read `LARCH_DYNAMIC_ARCHETYPES_MAX` from session-env first (matching `run-step5-review.sh`), fall back to non-empty process env only when session-env is empty, then default to `6`; validate after resolution; add a harness case with conflicting session-env vs ambient values asserting banner matches forwarded CLI.
  - From dyn-step5-runtime-output.txt: Drop the dead `${dynamic_archetypes_value:-}` branch from the fence and align prose with the actual source order (session-env → ambient → default), or export a durable key into session-env only and read that single source in both the fence and `run-step5-review.sh`.


### FINDING_6: Step 5 telemetry fence adds an unpinned prompt-side KV contract and duplicated cap logic
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-make-harness-output.txt, dyn-quiet-contract-output.txt
- **Severity**: important
- **Concern**: The Step 5 telemetry fence now computes banner values, calls `lib-implement-round-cap.sh`, and emits ad-hoc stdout KVs that prompt-side orchestration must parse. This duplicates runtime precedence logic, expands beyond the plan’s intended prose-only degraded-round directive, and lacks CI structure tests pinning the CLI call and emitted KV names.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Revert to prose-only CLI directive per plan or add structure harness pinning fence CLI invocation and KV printf lines
  - From cursor-specialist-testing-output.txt: Extend test-implement-structure.sh Step 5 region to require --count-prior-degraded and emitted KV line patterns
  - From dyn-make-harness-output.txt: Either revert to the plan’s prose-only CLI directive (`lib-implement-round-cap.sh --count-prior-degraded …` in orchestrator prose, no expanded fence), or add a `scripts/test-implement-structure.sh` assertion that the Step 5 region contains `--count-prior-degraded` and the four `printf` KV lines.
  - From dyn-quiet-contract-output.txt: Revert the fence to telemetry-only (as in `1bd5a94a1`); keep the degraded-round fix as a single CLI invocation in prose or one assignment line, without moving the full `dynamic_archetypes_cap` derivation into the fence.


### FINDING_9: Happy-path append test does not prove entries land under `Warnings`
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The append-execution happy-path test only checks that the file contains both the `Warnings` header and the entry somewhere. A regression inserting the warning under another section would still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Extract the Warnings section or add a following header and assert the entry appears before the next section.


