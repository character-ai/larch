### OOS_1: [OUT_OF_SCOPE] kv CLI is thin glue over existing KV parsing helpers
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The `kv_cli.py` migration is thin glue over `larch.io.kv_value` / `read_kv`, and the io-layer tests already cover the edge cases named in the review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] pause last-match semantics stay aligned
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The new `pause --match last` path still matches the prior `awk ... | tail -1` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] release Step 8 fallbacks preserve prior behavior
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The `-z` checks and `${VAR:-false}` fallbacks still behave like the old awk paths for `false`, empty, and missing keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] deps parsing keeps first-equals semantics
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The `REPO` and `ORIGIN_SLUG` parsing still keeps everything after the first `=` through `read_kv`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] kv get remains registered as quiet-safe stdout
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The `("kv", "get")` registry entry and its explicit test keep the quiet-mode corruption risk covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] deps argv dispatch still carries renderer-stripping risk
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: The surviving inline `case "$1"` / `"$2"` dispatch in `skills/deps/SKILL.md` still depends on prompt-side shell rendering, so the original failure mode remains there.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Out of plan scope here; a follow-up could move argv parsing behind a `python/cli.py` verb or another renderer-safe pattern.
  - From cursor-specialist-testing: Out of scope per plan non-goals; migrate behind cli.py or extend lint if pursued later

### OOS_7: [OUT_OF_SCOPE] reference snippets remain outside the lint scope
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The lint only scans skill prompts, not `references/*.md`, so bootstrap snippets in implement references can still keep the old awk idiom.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Extend lint scope or migrate reference snippets in a follow-up if implement stalls trace back to reference loading.

### OOS_8: [OUT_OF_SCOPE] implement keeps the bootstrap awk exemption
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The documented lint exemption leaves the bootstrap `$0` awk one-liner in a frequently loaded skill path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Accept as documented non-goal, or pursue an upstream renderer fix; a `kv get` helper cannot run before `CLAUDE_PLUGIN_ROOT` is known.

### OOS_9: [OUT_OF_SCOPE] release/deps migrations lack an integration harness
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The release Step 8 and deps `resolve.env` migrations do not have a bash or CLI harness yet, so wiring mistakes are not caught automatically.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

