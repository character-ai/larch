## Proposed Design Outline

### Goals
- Surface an actionable "upgrade Codex CLI" message when OpenAI's per-model version gate trips, replacing the opaque `exit 99` + vague CLI warning.
- Switch the Step 0 codex probe to exercise `gpt-5.6-luna` (cheapest, highest-volume review model) instead of `gpt-5.6-sol`.
- Route the detected gate signal to `/implement`'s Step 2 drift warning and to `/larch:status`.

### Non-goals
- No `codex --version` version-floor constant or check.
- No probing of sol/terra in Step 0 (single luna probe only).
- No change to the 60s probe cache TTL, the exit-99 launcher sentinel, or the degraded-tools gate stdout contract.

### Approach sketch
- Add one shared detector that matches `Model metadata for <model> not found` and `requires a newer version of Codex` in stderr/sidecar text and returns the gated model plus upgrade hint.
- Probe path (`_auth.py`): switch probe model to luna; when the detector fires, mark codex unavailable with a gate-specific reason feeding the status state/phrase.
- Launch path: classify the gate signal into an actionable failure reason surfaced through the codex `claude_fallback` drift warning.
- `/larch:status` and the shared degraded explanation: render the upgrade hint when the probe hit the gate.

### Surfaces in scope
- `python/larch/agents/_auth.py` (probe model, status state/phrase).
- `python/larch/agents/_run_external.py` and/or `collect_results.py` (shared detector + launch classification).
- `python/larch/implement/dispatch_step2.py` (emit hint on codex fallback).
- `skills/implement/SKILL.md` and `skills/status/SKILL.md` (message rendering).
- Tests under `python/tests/agents/` and `python/tests/implement/`.

### Open questions
- None.
