# scripts/lib-gemini-tool-drift.sh — contract

`scripts/lib-gemini-tool-drift.sh` is a sourced-only shell library (no shebang, not invokable directly) owned by `scripts/check-reviewers.sh`. It parses `scripts/gemini-reviewer-policy.toml` as the reviewer write-tool deny-list source of truth, verifies `scripts/gemini-known-tools.txt` checksums, discovers live Gemini tool names best-effort, emits `GEMINI_TOOL_DRIFT_WARNING=` / `GEMINI_TOOL_DRIFT_ARTIFACT=`, and flips `GEMINI_HEALTHY=false` when an observed or fixture-known write-style tool is missing from the deny list.

The primary contract lives in `scripts/check-reviewers.md`; this sibling exists for discoverability per the AGENTS.md per-script-contract convention. Do NOT invoke this library directly. Edits must update `scripts/check-reviewers.sh`, `scripts/check-reviewers.md`, `scripts/test-check-reviewers.sh`, `scripts/gemini-known-tools.txt`, `scripts/gemini-known-tools.md`, and `SECURITY.md` as applicable.
