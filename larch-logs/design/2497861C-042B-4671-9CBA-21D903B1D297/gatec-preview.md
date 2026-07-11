## Final Design Plan

## Plan

## Approach

Add a Step 2-specific Cursor model map keyed by normalized difficulty.

Pass the selected default through the shared model resolver. Keep its precedence:

1. `LARCH_CURSOR_MODEL`
2. `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL`
3. Caller-provided Step 2 default
4. Global `CURSOR_DEFAULT_MODEL`

Forward `--difficulty` from the Step 2 dispatcher to the Cursor implement launcher. Use the selected model in both the Cursor command and usage sidecar. Do not change vendor ordering, Codex model selection, or other Cursor launchers.

## Files to modify/create

### UPDATED: python/larch/core/config.py

- Add `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY` beside the existing Cursor and difficulty constants.
- Map TRIVIAL and HARD to `CURSOR_DEFAULT_MODEL`.
- Map MODERATE to `"grok-4.5"`.
- Keep `CURSOR_DEFAULT_MODEL` unchanged so non-Step-2 consumers still default to `composer-2.5`.
- Do not modify `CODER_TOOL_ORDER_BY_DIFFICULTY` or `CODEX_IMPLEMENT_MODEL_BY_DIFFICULTY`.

### UPDATED: python/larch/implement/dispatch_step2.py

- Forward the resolved Step 2 difficulty through `_launcher_args` for Cursor launches.
- Update `_resolve_implement_rater_model` to select the Cursor fallback from `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY`.
- Fall back to `CURSOR_DEFAULT_MODEL` when the tier is absent or unknown.
- Preserve environment and session option precedence.
- Ensure the model recorded in the difficulty and usage metadata matches the model selected for that tier.
- Leave Codex resolution unchanged so a MODERATE Cursor-to-Codex fallback remains `gpt-5.6-sol`.

### UPDATED: python/larch/agents/_launch_failure.py

- Make the Cursor branch of `resolve_model_args` honor its `default_model` argument.
- Retain `CURSOR_DEFAULT_MODEL` when the caller supplies no default.
- Keep `LARCH_CURSOR_MODEL` ahead of `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL`, and keep both ahead of the caller default.
- Preserve blank-value and control-character validation.

### UPDATED: python/larch/agents/_ci_launcher.py

- In `launch_cursor_implement_main`, normalize `args.difficulty`.
- Resolve the Step 2 Cursor default through `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY`.
- Pass that default to `resolve_model_args`.
- Use the resolved command model when recording Cursor usage so MODERATE rows include `model=grok-4.5`.
- Do not apply the map to the CI fixer or any other Cursor launcher.

### UPDATED: python/tests/core/test_config.py

- Assert that `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY` covers all three supported tiers.
- Assert TRIVIAL and HARD resolve to `CURSOR_DEFAULT_MODEL`.
- Assert MODERATE resolves to `grok-4.5`.
- Assert the global Cursor default remains `composer-2.5`.

### UPDATED: python/tests/implement/test_implement_dispatch.py

- Cover Cursor rater-model resolution for TRIVIAL, MODERATE, HARD, and missing difficulty.
- Assert MODERATE resolves to `grok-4.5`; TRIVIAL, HARD, and missing difficulty resolve to `composer-2.5`.
- Parametrize `LARCH_CURSOR_MODEL` and `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL` override cases across TRIVIAL, MODERATE, and HARD.
- Assert each override wins over its tier default, including that MODERATE resolves to the override rather than `grok-4.5`.
- Assert `LARCH_CURSOR_MODEL` wins when both overrides are present at every tier.
- Assert Cursor launcher arguments include the resolved `--difficulty`.
- Retain or add a MODERATE Codex assertion for `gpt-5.6-sol` to protect the fallback lane.

### UPDATED: python/tests/agents/test_agents.py

- Assert `resolve_model_args("cursor", default_model=...)` forwards the caller default when no override exists.
- Assert both Cursor override sources still beat the supplied default.
- Exercise `launch_cursor_implement_main` across TRIVIAL, MODERATE, and HARD and inspect the model passed to the launcher.
- Assert the MODERATE command contains `--model grok-4.5`.
- Assert TRIVIAL and HARD contain `--model composer-2.5`.
- Capture usage recording and assert the resolved model is passed through, producing MODERATE attribution as `model=grok-4.5`.
- Keep a regression assertion that the non-Step-2 Cursor CI fixer still resolves its existing `composer-2.5` default.

## Edge cases

- An omitted or unrecognized internal difficulty value must use `CURSOR_DEFAULT_MODEL`.
- A valid but blank override must continue to fail validation rather than silently use the tier default.
- Process environment values must continue to outrank session or plugin values.
- Model metadata must use the final resolved model, including overrides, not merely the tier default.
- Cursor unavailability at MODERATE must not alter the Codex fallback model.

## Failure modes

- Selecting `grok-4.5` in the dispatcher but not the launcher would produce incorrect command arguments.
- Selecting the right command model but recording the static default would misprice usage sidecars.
- Applying the map inside the shared resolver without a caller default would change non-Step-2 Cursor behavior.
- Reversing override precedence would break operator configuration.
- Testing overrides only with missing difficulty would leave MODERATE precedence over `grok-4.5` unverified.
- Failing to forward difficulty would make every Cursor launch use the global default.

## Testing strategy

Run the focused tests for all firm test surfaces:

- `python3 -m pytest python/tests/core/test_config.py`
- `python3 -m pytest python/tests/implement/test_implement_dispatch.py`
- `python3 -m pytest python/tests/agents/test_agents.py`

Run changed-file lint and type checks through the repository’s documented Python lint path. Confirm tests inspect command arguments and usage-recording inputs rather than invoking a live Cursor process.

Confidence: high. The relevant model resolver, Step 2 launcher, usage recorder, and existing tests provide direct seams for the change.

difficulty: MODERATE
diff_added: 160
diff_deleted: 15
mechanical_churn: false
diff_lines: 175
