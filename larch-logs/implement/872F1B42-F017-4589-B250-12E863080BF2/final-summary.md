## /implement run 872F1B42-F017-4589-B250-12E863080BF2: shipping

- **Outcome**: shipping
- Force: true
- **Duration**: 00:22:28
- **Cost**: 💰 TOTAL ~$9.86: Claude $8.17, Codex-5.5 $1.56, Codex-mini $0.00, Cursor $0.00, Claude (subprocess) $0.13  |  Tokens: 11166k
- **Issue**: #6590: https://github.com/character-ai/larch/issues/6590
- **Plan review**: N/A
- **Difficulty**: predicted MODERATE; applied MODERATE; panel skipped: self-review
- **Dynamic archetypes**: N/A
- **Code review**: self-review: 0 findings
- **Lines (PR diff)**: N/A
- **OOS filed**: 0
- **Exec issues**: 0
- **Warnings**: 5
- **Run logs**: `larch-logs/implement/872F1B42-F017-4589-B250-12E863080BF2/`
- **Main agent model**: claude-opus-4-8
- **Effort**: max
- **Larch version**: 52.5.7

<!-- larch:run-summary v=1 -->

## Exec Issues and Warnings
Exec Issues (0):
Warnings (5):
  1. Step 5: self-review mode: main-agent inline review complete
  2. Step 7a: bgjob launch first failed with `missing session owner pid`; the step-7a Python launch (`_launch_step7a_bgjob`) passes no `--owner-pid` and the ephemeral Bash shell had no owner-pid env var...
  3. Consulted ARCHITECTURAL_GUIDELINES.md against the final diff (`python/larch/bgjob/cli.py`, `python/tests/bgjob/test_bgjob_cli.py`).
  4. G-Fix-1 (fix the class, not the instance): the sibling `start_main` / `_build_spec` shares the `Path(args.tmpdir)` shape behind the empty-arg bug but is left unchanged. `bgjob start` keeps `--tmpdi...
  5. No other deviations. G-Cfg-1: the fix uses the `config.ENV_IMPLEMENT_TMPDIR` Final, not a string literal. G-Py-4: an empty tmpdir with no env fallback fails loud and closed (`BGJOB_ERROR=missing-tm...

## Review Phase Detail

No review rounds completed.

## Architectural guidelines

Consulted ARCHITECTURAL_GUIDELINES.md against the final diff (`python/larch/bgjob/cli.py`, `python/tests/bgjob/test_bgjob_cli.py`).

- G-Fix-1 (fix the class, not the instance): the sibling `start_main` / `_build_spec` shares the `Path(args.tmpdir)` shape behind the empty-arg bug but is left unchanged. `bgjob start` keeps `--tmpdir` required, and every caller (`run-step-checks.sh`, `step-6-entry.sh`, `step-8-ship.sh`, `step_7a.py`) supplies a non-empty env-derived tmpdir, so `start` cannot reach the empty-arg path. The descope is intentional and matches the issue's open questions. Recorded here per the "sibling provably unreachable" carve-out.

No other deviations. G-Cfg-1: the fix uses the `config.ENV_IMPLEMENT_TMPDIR` Final, not a string literal. G-Py-4: an empty tmpdir with no env fallback fails loud and closed (`BGJOB_ERROR=missing-tmpdir`, rc 2). G-Wire-1: the new `BGJOB_ERROR=` line is additive on a new error path; the success-path `BGJOB_STATUS=` grammar is unchanged.
