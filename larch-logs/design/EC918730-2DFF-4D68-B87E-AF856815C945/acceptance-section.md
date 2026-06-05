## Acceptance

- `round_artifact_included()` in `scripts/larch-log.sh` has an explicit dynamic-Codex allow clause placed after all existing deny clauses (through the zero-byte placeholder deny and the static `codex-specialist-*` deny) and before the broad `*-output.txt` allow. It allows `dyn-*-codex-output.txt`, `dyn-*-codex-output-phase*.txt`, and their `.meta` / `.json` / `.cap-hit` sidecars. It uses no catch-all `dyn-*-codex-output-*.txt` suffix glob.
- `bash scripts/test-larch-log-write-round.sh` passes with new coverage: phased dynamic-Codex `.txt` / `.meta` / `.json` / `.cap-hit` included; `.cap-hit` for unphased dynamic Codex included; `.prompt`, dynamic-shaped `*-vote-prompt.txt`, and unphased `.events.jsonl` excluded; raw static `codex-specialist-security-output.txt` excluded; phased static `codex-specialist-security-output-phase2.txt` + `.meta` included.
- `scripts/larch-log.md` (write-round enumeration) and `scripts/test-larch-log-write-round.md` document the explicit dynamic-Codex retention contract (phased + unphased; sidecar inclusions and exclusions) with no catch-all suffix glob.
- `bash scripts/test-larch-log.sh` passes.
- `bash scripts/relevant-checks.sh` passes.
- Behavior-preserving: which artifacts are committed for pre-existing inputs is unchanged; the new clause makes the already-effective dynamic-Codex inclusion explicit and regression-proof.
