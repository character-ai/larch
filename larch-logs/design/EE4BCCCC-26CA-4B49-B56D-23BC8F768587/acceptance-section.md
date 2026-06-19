## Acceptance

- All live consumers of the 16 helpers call `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb>` (skill `.md` fences, docs, `Makefile`, `.github/` CI, `python/*.py` callers, dev-only skills).
- `push checkpoint-probe` reaches parity with `rebase-checkpoint-probe.sh` before deletion: `--forked-target` fork defaulting to `upstream/main`, `ROUTE=continue|conflict|bail`, the `larch-logs/*` trivial-conflict pre-pass (resolve, continue, consecutive-trivial loop, mixed-conflict `CONFLICT_FILES` re-derivation, empty-continue skip), and `SKIPPED_ALREADY_PUSHED` precedence; covered by focused `python/test_push.py` cases mirroring harness cases 17-24.
- The 16 `.sh` files plus their `.md` contracts and `test-*` `.sh`/`.md` siblings are deleted with no stubs.
- Missed reference surfaces are repointed or have obsolete assertions removed: `scripts/extract-closes-issue-from-pr.sh`, `scripts/lib-phantom-probe.md`, `skills/shared/skill-design-principles.md`, the four `test-implement-*` structural harnesses, `skills/implement/scripts/test-step-7a.sh`, and `step-7a.md`.
- `python/migrated-scripts.tsv` has one row per deleted path tagged `#4642`; no retired-path literals appear in test fixtures (paths built at runtime).
- `make lint-retired-scripts`, `make py-lint`, `make py-test`, and `make lint` (including structural harness shards 4, 14, 16) all pass.
